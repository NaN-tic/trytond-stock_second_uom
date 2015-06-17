# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval

__all__ = ['PurchaseLine']
__metaclass__ = PoolMeta

STATES = {
    'invisible': (Eval('type') != 'line') | ~Eval('use_second_unit', False),
    'required': (Eval('type') == 'line') & Eval('use_second_unit', False),
    'readonly': ~Eval('_parent_sale', {}),
    }
DEPENDS = ['type', 'use_second_unit']


class PurchaseLine:
    __name__ = 'purchase.line'
    use_second_unit = fields.Function(fields.Boolean('Use Second Unit'),
        'on_change_with_use_second_unit')
    second_quantity = fields.Float("Second Quantity",
        digits=(16, Eval('second_unit_digits', 2)),
        states=STATES, depends=DEPENDS + ['second_unit_digits'])
    second_unit = fields.Many2One("product.uom", "Second Unit", domain=[
            ('category', '=', Eval('product_second_uom_category')),
            ],
        states=STATES, depends=DEPENDS + ['product_second_uom_category'])
    second_unit_digits = fields.Function(fields.Integer('Second Unit Digits'),
        'on_change_with_second_unit_digits')
    product_second_uom_category = fields.Function(
        fields.Many2One('product.uom.category', 'Product Second UoM Category'),
        'on_change_with_product_second_uom_category')

    @fields.depends('product')
    def on_change_with_use_second_unit(self, name=None):
        if self.product and self.product.use_second_uom:
            return True
        return False

    @fields.depends('second_unit')
    def on_change_with_second_unit_digits(self, name=None):
        if self.second_unit:
            return self.second_unit.digits
        return 2

    @fields.depends('product')
    def on_change_with_product_second_uom_category(self, name=None):
        if self.product and self.product.use_second_uom:
            return self.product.second_uom.category.id

    @fields.depends('product', 'second_unit')
    def on_change_product(self):
        res = super(PurchaseLine, self).on_change_product()
        if self.product and self.product.use_second_uom:
            if (not self.second_unit
                    or self.second_unit.category
                    != self.product.second_uom.category):
                self.second_unit = self.product.second_uom
                res['second_unit'] = self.product.second_uom.id
                res['second_unit.rec_name'] = self.product.second_uom.rec_name
                res['second_unit_digits'] = self.product.second_uom.digits
        return res

    def get_move(self):
        pool = Pool()
        Uom = pool.get('product.uom')

        move = super(PurchaseLine, self).get_move()

        if move and self.use_second_unit:
            skip = set(self.moves_recreated)
            second_quantity = abs(self.second_quantity)
            for move in self.moves:
                if move not in skip:
                    second_quantity -= Uom.compute_qty(
                        move.second_uom,
                        move.second_quantity,
                        self.second_unit)

            second_quantity = max(
                Uom.round(second_quantity, self.second_unit.rounding), 0)
            move.second_quantity = second_quantity
            move.second_uom = self.second_unit
        return move
