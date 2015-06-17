# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval
from trytond.modules.product.product import STATES, DEPENDS

__all__ = ['Template', 'Product']
__metaclass__ = PoolMeta

STATES_SU = STATES.copy()
STATES_SU['required'] = Eval('use_second_uom', False)
DEPENDS_SU = DEPENDS[:] + ['use_second_uom']


class Template:
    __name__ = "product.template"
    use_second_uom = fields.Function(fields.Boolean('Use Second UOM'),
        'on_change_with_use_second_uom', searcher='search_use_second_uom')
    second_uom = fields.Many2One('product.uom', 'Second UoM',
        states=STATES_SU, depends=DEPENDS_SU)
    second_quantity = fields.Function(fields.Float('Second UoM Quantity',
            states={
                'invisible': ~Eval('use_second_uom', False),
                }, depends=['use_second_uom']),
        'sum_product')
    second_forecast_quantity = fields.Function(
        fields.Float('Second UoM Forecast Quantity', states={
                'invisible': ~Eval('use_second_uom', False),
                }, depends=['use_second_uom']),
        'sum_product')

    @classmethod
    def __setup__(cls):
        super(Template, cls).__setup__()
        if hasattr(cls, 'main_products'):
            cls.on_change_with_use_second_uom.depends.add('main_products')
            cls.on_change_with_use_second_uom.depends.add('raw_products')
        cls._error_messages.update({
                'change_second_uom': ('You cannot change the second uom for '
                    'a product which is associated to stock moves.'),
                })
        cls._modify_no_move.append(('second_uom', 'change_second_uom'))

    @fields.depends('products')
    def on_change_with_use_second_uom(self, name=None):
        if hasattr(self, 'main_products'):
            return (any(p.use_second_uom for p in self.main_products)
                | any(p.use_second_uom for p in self.raw_products))
        return any(p.use_second_uom for p in self.products)

    @classmethod
    def search_use_second_uom(cls, name, clause):
        return [('products.use_second_uom', ) + tuple(clause[1:])]

    def sum_product(self, name):
        if name in ('second_quantity', 'second_forecast_quantity'):
            sum_ = 0.
            for product in self.products:
                qty = getattr(product, name)
                if qty:
                    sum_ += qty
            return sum_
        return super(Template, self).sum_product(name)


class Product:
    __name__ = "product.product"
    use_second_uom = fields.Boolean('Use Second UoM', states=STATES,
        depends=DEPENDS)
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

    @classmethod
    def __setup__(cls):
        super(Product, cls).__setup__()
        cls._error_messages.update({
                'second_uom_required': ('The Second UoM must be set on '
                    'template because product "%s" is set to Use Second UoM.'),
                })

    def get_second_uom(self, name):
        if self.template.second_uom:
            return self.template.second_uom.id

    @classmethod
    def search_second_uom(cls, name, clause):
        return [('template.second_uom',) + tuple(clause[1:])]

    @classmethod
    def validate(cls, products):
        super(Product, cls).validate(products)
        for product in products:
            product.check_second_uom()

    def check_second_uom(self):
        if self.use_second_uom and not self.template.second_uom:
            self.raise_user_error('second_uom_required', self.rec_name)

    @classmethod
    def _quantity_context(cls, name):
        if name.startswith('second_'):
            context = super(Product, cls)._quantity_context(name[7:])
            context['second_uom'] = True
            return context
        return super(Product, cls)._quantity_context(name)
