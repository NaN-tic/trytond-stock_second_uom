# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .product import *
from .stock import *
from .sale import *
from .purchase import *


def register():
    Pool.register(
        Template,
        Product,
        Lot,
        Move,
        ShipmentIn,
        ShipmentOut,
        ShipmentOutReturn,
        PeriodCache,
        PeriodCacheLot,
        Inventory,
        InventoryLine,
        SaleLine,
        PurchaseLine,
        module='stock_second_uom', type_='model')
    Pool.register(
        ReturnSale,
        module='stock_second_uom', type_='wizard')
