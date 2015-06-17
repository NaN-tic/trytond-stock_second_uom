# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from sql import Join, Literal, Select, Table, Union
from sql.aggregate import Sum
from sql.conditionals import Coalesce
from sql.operators import Neg

from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, In
from trytond.transaction import Transaction

__all__ = ['Lot', 'Move', 'ShipmentIn', 'ShipmentOut', 'ShipmentOutReturn',
    'PeriodCache', 'PeriodCacheLot', 'Inventory', 'InventoryLine']
__metaclass__ = PoolMeta

STATES = {
    'readonly': In(Eval('state'), ['cancel', 'done']),
    'invisible': ~Eval('use_second_uom', False),
    }
DEPENDS = ['state', 'use_second_uom']


class Lot:
    __name__ = 'stock.lot'
    use_second_uom = fields.Function(fields.Boolean('Use Second UOM'),
        'get_use_second_uom', searcher='search_use_second_uom')
    second_uom = fields.Function(fields.Many2One('product.uom', 'Second UoM'),
        'get_second_uom', searcher='search_second_uom')
    second_quantity = fields.Function(fields.Float('Second UoM Quantity',
            states={
                'invisible': ~Eval('use_second_uom', False),
                }, depends=['use_second_uom']),
        'get_quantity', searcher='search_quantity')
    second_forecast_quantity = fields.Function(
        fields.Float('Second UoM Forecast Quantity', states={
                'invisible': ~Eval('use_second_uom', False),
                }, depends=['use_second_uom']),
        'get_quantity', searcher='search_quantity')

    def get_use_second_uom(self, name=None):
        return self.product.use_second_uom

    @classmethod
    def search_use_second_uom(cls, name, clause):
        return [('product.use_second_uom', ) + tuple(clause[1:])]

    def get_second_uom(self, name):
        if self.product.second_uom:
            return self.product.second_uom.id

    @classmethod
    def search_second_uom(cls, name, clause):
        return [('product.second_uom',) + tuple(clause[1:])]

    @classmethod
    def _quantity_context(cls, name):
        if name.startswith('second_'):
            context = super(Lot, cls)._quantity_context(name[7:])
            context['second_uom'] = True
            return context
        return super(Lot, cls)._quantity_context(name)


class Move:
    __name__ = 'stock.move'
    use_second_uom = fields.Function(fields.Boolean('Use Second UoM'),
        'on_change_with_use_second_uom')
    product_second_uom_category = fields.Function(
        fields.Many2One('product.uom.category', 'Product Second UoM Category'),
        'on_change_with_product_second_uom_category')
    second_uom = fields.Many2One("product.uom", "Second UoM", domain=[
            ('category', '=', Eval('product_second_uom_category')),
            ],
        states=STATES, depends=DEPENDS + ['product_second_uom_category'])
    second_unit_digits = fields.Function(fields.Integer('Second Unit Digits'),
        'on_change_with_second_unit_digits')
    second_quantity = fields.Float("Second Quantity",
        digits=(16, Eval('second_unit_digits', 2)),
        states=STATES, depends=DEPENDS + ['second_unit_digits'])
    second_internal_quantity = fields.Float('Second Internal Quantity',
        readonly=True)

    @classmethod
    def __setup__(cls):
        super(Move, cls).__setup__()
        cls._error_messages.update({
                'second_uom_required': ('The Second UoM Quantity is required '
                    'for move of product "%s".'),
                'second_quantity_not_positive': (
                    'The Second UoM Quantity of move "%s" must be positive.'),
                })

    @fields.depends('product')
    def on_change_with_use_second_uom(self, name=None):
        if self.product and self.product.use_second_uom:
            return True
        return False

    @fields.depends('product')
    def on_change_with_product_second_uom_category(self, name=None):
        if self.product and self.product.use_second_uom:
            return self.product.second_uom.category.id

    @fields.depends('second_uom')
    def on_change_with_second_unit_digits(self, name=None):
        if self.second_uom:
            return self.second_uom.digits
        return 2

    @fields.depends('product', 'second_uom')
    def on_change_product(self):
        res = super(Move, self).on_change_product()
        if self.product and self.product.use_second_uom:
            if (not self.second_uom
                    or self.second_uom.category
                    != self.product.second_uom.category):
                self.second_uom = self.product.second_uom
                res['second_uom'] = self.product.second_uom.id
                res['second_uom.rec_name'] = self.product.second_uom.rec_name
        return res

    @classmethod
    def validate(cls, moves):
        super(Move, cls).validate(moves)
        for move in moves:
            move.check_second_uom_required()
            move.check_second_quantity_positive()

    def check_second_uom_required(self):
        "Check if second_uom is required"
        if (self.state == 'done'
                and self.use_second_uom
                and (self.second_quantity == None or not self.second_uom
                    or self.second_internal_quantity == None)):
            self.raise_user_error('second_uom_required', self.product.rec_name)

    def check_second_quantity_positive(self):
        "Check if second quantities are positive or 0"
        pool = Pool()
        InventoryLine = pool.get('stock.inventory.line')
        if self.origin and isinstance(self.origin, InventoryLine):
            return
        if (self.second_quantity and self.second_quantity < 0.
                or self.second_internal_quantity
                and self.second_internal_quantity < 0.):
            self.raise_user_error('second_quantity_not_positive',
                self.rec_name)

    @classmethod
    def compute_quantities_query(cls, location_ids, with_childs=False,
            grouping=('product',), grouping_filter=None):
        pool = Pool()
        Period = pool.get('stock.period')

        query = super(Move, cls).compute_quantities_query(
            location_ids, with_childs=with_childs, grouping=grouping,
            grouping_filter=grouping_filter)

        if query and Transaction().context.get('second_uom'):
            tables_to_find = [cls._table]
            for grouping in Period.groupings():
                Cache = Period.get_cache(grouping)
                if Cache:
                    tables_to_find.append(Cache._table)

            def second_qty_column(table):
                if table._name != cls._table:
                    return Coalesce(table.second_internal_quantity, Literal(0))
                return Sum(
                    Coalesce(table.second_internal_quantity, Literal(0)))

            def find_table(join):
                if not isinstance(join, Join):
                    return
                for pos in ['left', 'right']:
                    item = getattr(join, pos)
                    if isinstance(item, Table):
                        if item._name in tables_to_find:
                            return getattr(join, pos)
                    else:
                        return find_table(item)

            def find_queries(query):
                if isinstance(query, Union):
                    for sub_query in query.queries:
                        for q in find_queries(sub_query):
                            yield q
                elif isinstance(query, Select):
                    yield query

            union, = query.from_
            for sub_query in find_queries(union):
                # Find move table
                for table in sub_query.from_:
                    if (isinstance(table, Table)
                            and table._name in tables_to_find):
                        second_qty_col = second_qty_column(table)
                        break
                    found = find_table(table)
                    if found:
                        second_qty_col = second_qty_column(found)
                        break
                else:
                    # Not query on move table
                    continue

                columns = []
                for col in sub_query.columns:
                    if col.output_name == 'quantity':
                        if isinstance(col.expression, Neg):
                            columns.append(
                                (-second_qty_col).as_('quantity'))
                        else:
                            columns.append(
                                second_qty_col.as_('quantity'))
                    else:
                        columns.append(col)
                sub_query.columns = tuple(columns)
        return query

    @classmethod
    def create(cls, vlist):
        pool = Pool()
        Product = pool.get('product.product')
        Uom = pool.get('product.uom')

        vlist = [x.copy() for x in vlist]
        for vals in vlist:
            product = Product(vals['product'])
            if vals.get('second_uom') and vals.get('second_quantity'):
                second_uom = Uom(vals['second_uom'])
                second_internal_quantity = cls._get_second_internal_quantity(
                    vals['second_quantity'], second_uom, product)
                vals['second_internal_quantity'] = second_internal_quantity
        return super(Move, cls).create(vlist)

    @classmethod
    def write(cls, *args):
        super(Move, cls).write(*args)

        actions = iter(args)
        for moves, values in zip(actions, actions):
            for move in moves:
                if not move.second_uom or move.second_quantity == None:
                    continue
                second_internal_qty = cls._get_second_internal_quantity(
                    move.second_quantity, move.second_uom, move.product)
                if (second_internal_qty != move.second_internal_quantity
                        and second_internal_qty
                        != values.get('second_nternal_quantity')):
                    cls.write([move], {
                            'second_internal_quantity': second_internal_qty,
                            })

    @staticmethod
    def _get_second_internal_quantity(quantity, uom, product):
        Uom = Pool().get('product.uom')
        if product.second_uom:
            return Uom.compute_qty(uom, quantity,
                product.second_uom, round=True)


class ShipmentIn:
    __name__ = 'stock.shipment.in'

    @classmethod
    def _get_inventory_moves(cls, incoming_move):
        move = super(ShipmentIn, cls)._get_inventory_moves(incoming_move)
        if move and incoming_move.use_second_uom:
            move.second_quantity = incoming_move.second_quantity
            move.second_uom = incoming_move.second_uom
        return move


class ShipmentOut:
    __name__ = 'stock.shipment.out'

    def _get_inventory_move(self, move):
        inventory_move = super(ShipmentOut, self)._get_inventory_move(move)
        if move.use_second_uom:
            inventory_move.second_quantity = move.second_quantity
            inventory_move.second_uom = move.second_uom
        return inventory_move

    @classmethod
    def _sync_inventory_to_outgoing(cls, shipments):
        pool = Pool()
        Uom = pool.get('product.uom')
        super(ShipmentOut, cls)._sync_inventory_to_outgoing(shipments)
        for shipment in shipments:
            outgoing_by_product = {}
            for move in shipment.outgoing_moves:
                if not move.use_second_uom:
                    continue
                outgoing_by_product.setdefault(move.product.id,
                    []).append(move)
            for move in shipment.inventory_moves:
                if not move.use_second_uom:
                    continue
                out_move = outgoing_by_product[move.product.id][0]
                if out_move.second_uom and out_move.second_quantity:
                    out_move.second_quantity += Uom.compute_qty(
                        move.second_uom,
                        move.second_quantity,
                        out_move.second_uom)
                    out_move.save()
                else:
                    out_move.second_quantity = move.second_quantity
                    out_move.second_uom = move.second_uom
                    out_move.save()


class ShipmentOutReturn:
    __name__ = 'stock.shipment.out.return'

    @classmethod
    def _get_inventory_moves(cls, incoming_move):
        move = super(ShipmentOutReturn,
            cls)._get_inventory_moves(incoming_move)
        if move and incoming_move.use_second_uom:
            move.second_quantity = incoming_move.second_quantity
            move.second_uom = incoming_move.second_uom
        return move


class PeriodCache:
    __name__ = 'stock.period.cache'
    second_internal_quantity = fields.Float('Second Internal Quantity',
        readonly=True)

    @classmethod
    def create(cls, vlist):
        pool = Pool()
        Period = pool.get('stock.period')
        Product = pool.get('product.product')

        vlist_by_period_location = {}
        for values in vlist:
            vlist_by_period_location.setdefault(values['period'], {})\
                .setdefault(values['location'], []).append(values)

        vlist = []
        for period_id, vlist_by_location in \
                vlist_by_period_location.iteritems():
            period = Period(period_id)
            with Transaction().set_context(
                    stock_date_end=period.date,
                    stock_date_start=None,
                    stock_assign=False,
                    forecast=False,
                    stock_destinations=None,
                    second_uom=True,
                    ):
                pbl = Product.products_by_location(
                    vlist_by_location.keys(), grouping=('product',))
            for location_id, location_vlist in vlist_by_location.iteritems():
                for values in location_vlist:
                    key = (location_id, values['product'])
                    values['second_internal_quantity'] = pbl.get(key, 0.0)
                    vlist.append(values)
        return super(PeriodCache, cls).create(vlist)


class PeriodCacheLot:
    __name__ = 'stock.period.cache.lot'
    second_internal_quantity = fields.Float('Second Internal Quantity',
        readonly=True)

    @classmethod
    def create(cls, vlist):
        pool = Pool()
        Period = pool.get('stock.period')
        Product = pool.get('product.product')

        vlist_by_period_location = {}
        for values in vlist:
            vlist_by_period_location.setdefault(values['period'], {})\
                .setdefault(values['location'], []).append(values)

        vlist = []
        for period_id, vlist_by_location in \
                vlist_by_period_location.iteritems():
            period = Period(period_id)
            with Transaction().set_context(
                    stock_date_end=period.date,
                    stock_date_start=None,
                    stock_assign=False,
                    forecast=False,
                    stock_destinations=None,
                    second_uom=True,
                    ):
                pbl = Product.products_by_location(
                    vlist_by_location.keys(), grouping=('product', 'lot'))
            for location_id, location_vlist in vlist_by_location.iteritems():
                for values in location_vlist:
                    key = (location_id, values['product'], values['lot'])
                    values['second_internal_quantity'] = pbl.get(key, 0.0)
                    vlist.append(values)
        return super(PeriodCacheLot, cls).create(vlist)


class Inventory:
    __name__ = 'stock.inventory'

    @classmethod
    def complete_lines(cls, inventories):
        pool = Pool()
        Line = pool.get('stock.inventory.line')
        Product = pool.get('product.product')

        super(Inventory, cls).complete_lines(inventories)

        grouping = cls.grouping()
        to_create = []
        for inventory in inventories:
            # Compute product second quantities
            with Transaction().set_context(
                    stock_date_end=inventory.date,
                    second_uom=True):
                pbl = Product.products_by_location(
                    [inventory.location.id], grouping=grouping)

            # Index some data
            product2type = {}
            product2consumable = {}
            for product in Product.browse([line[1] for line in pbl]):
                if not product.use_second_uom:
                    continue
                product2type[product.id] = product.type
                product2consumable[product.id] = product.consumable

            # Update existing lines
            to_write = []
            for line in inventory.lines:
                if not line.product.use_second_uom:
                    continue
                key = (inventory.location.id,) + line.unique_key
                if key in pbl:
                    second_qty = pbl.pop(key)
                else:
                    second_qty = 0.0
                if (line.second_quantity == line.second_expected_quantity
                            == second_qty):
                    continue
                values = {
                    'second_expected_quantity': second_qty,
                    }
                if line.second_quantity == line.second_expected_quantity:
                    values['second_quantity'] = max(second_qty, 0.0)
                to_write.extend(([line], values))
            if to_write:
                Line.write(*to_write)

            # Create lines if needed
            for key, second_qty in pbl.iteritems():
                product_id = key[grouping.index('product') + 1]
                if not second_qty:
                    continue
                if (product2type[product_id] != 'goods'
                        or product2consumable[product_id]):
                    continue

                values = Line.create_values4complete(inventory, 0.)
                for i, fname in enumerate(grouping, 1):
                    values[fname] = key[i]
                values['second_expected_quantity'] = second_qty
                values['second_quantity'] = max(second_qty, 0.0)
                to_create.append(values)
        if to_create:
            Line.create(to_create)


class InventoryLine:
    __name__ = 'stock.inventory.line'
    use_second_uom = fields.Function(fields.Boolean('Use Second UoM'),
        'on_change_with_use_second_uom')
    second_uom = fields.Function(fields.Many2One('product.uom', 'Second UoM',
            states={
                'invisible': ~Eval('use_second_uom', False),
                }, depends=['use_second_uom']),
        'get_second_uom')
    second_unit_digits = fields.Function(fields.Integer('Second Unit Digits'),
        'get_second_unit_digits')
    second_expected_quantity = fields.Float('Second UoM Expected Quantity',
        digits=(16, Eval('unit_digits', 2)), readonly=True, states={
            'required': Eval('use_second_uom', False),
            'invisible': ~Eval('second_uom', False),
            }, depends=['unit_digits', 'use_second_uom'])
    second_quantity = fields.Float('Second Quantity',
        digits=(16, Eval('unit_digits', 2)), states={
            'required': Eval('use_second_uom', False),
            'invisible': ~Eval('second_uom', False),
            }, depends=['unit_digits', 'use_second_uom'])

    @fields.depends('product')
    def on_change_product(self):
        change = super(InventoryLine, self).on_change_product()
        if self.product and self.product.use_second_uom:
            change['second_uom'] = self.product.second_uom.id
            change['second_uom.rec_name'] = self.product.default_uom.rec_name
            change['unit_digits'] = self.product.default_uom.digits
        else:
            change['second_uom'] = None
            change['second_unit_digits'] = 2
        return change

    @fields.depends('product')
    def on_change_with_use_second_uom(self, name=None):
        if self.product and self.product.use_second_uom:
            return True
        return False

    def get_second_uom(self, name):
        if self.use_second_uom:
            return self.product.second_uom.id

    @staticmethod
    def default_unit_digits():
        return 2

    def get_second_unit_digits(self, name):
        if self.product.second_uom:
            return self.product.second_uom.digits
        return self.default_unit_digits()

    @staticmethod
    def default_second_expected_quantity():
        return 0.

    def get_move(self):
        pool = Pool()
        Move = pool.get('stock.move')
        Uom = pool.get('product.uom')

        move = super(InventoryLine, self).get_move()
        if not self.use_second_uom:
            return move

        delta_second_qty = Uom.compute_qty(self.second_uom,
            self.second_expected_quantity - self.second_quantity,
            self.second_uom)
        if delta_second_qty == 0.0:
            if move:
                move.second_quantity = 0.
                move.second_uom = self.second_uom
            return move

        from_location = self.inventory.location
        to_location = self.inventory.lost_found
        if move:
            if move.from_location == to_location:  # inverse move
                delta_second_qty = -delta_second_qty
            move.second_quantity = delta_second_qty
            move.second_uom = self.second_uom
            return move

        if delta_second_qty < 0:
            (from_location, to_location, delta_second_qty) = \
                (to_location, from_location, -delta_second_qty)
        return Move(
            from_location=from_location,
            to_location=to_location,
            product=self.product,
            quantity=0.,
            uom=self.uom,
            second_quantity=delta_second_qty,
            second_uom=self.second_uom,
            company=self.inventory.company,
            effective_date=self.inventory.date,
            origin=self,
            )

    @classmethod
    def create_values4complete(cls, inventory, quantity):
        values = super(InventoryLine, cls).create_values4complete(
            inventory, quantity)
        values['second_quantity'] = 0.
        return values
