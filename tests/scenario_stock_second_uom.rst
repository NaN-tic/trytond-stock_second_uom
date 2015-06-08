===================
Second UoM Scenario
===================

=============
General Setup
=============

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from proteus import config, Model, Wizard
    >>> today = datetime.date.today()
    >>> last_month = today - relativedelta(months=1)

Create database::

    >>> config = config.set_trytond()
    >>> config.pool.test = True

Install stock_second_uom Module::

    >>> Module = Model.get('ir.module.module')
    >>> stock_module, = Module.find([('name', '=', 'stock_second_uom')])
    >>> stock_module.click('install')
    >>> Wizard('ir.module.module.install_upgrade').execute('upgrade')

Create company::

    >>> Currency = Model.get('currency.currency')
    >>> CurrencyRate = Model.get('currency.currency.rate')
    >>> Company = Model.get('company.company')
    >>> Party = Model.get('party.party')
    >>> company_config = Wizard('company.company.config')
    >>> company_config.execute('company')
    >>> company = company_config.form
    >>> party = Party(name='Dunder Mifflin')
    >>> party.save()
    >>> company.party = party
    >>> currencies = Currency.find([('code', '=', 'USD')])
    >>> if not currencies:
    ...     currency = Currency(name='US Dollar', symbol='$', code='USD',
    ...         rounding=Decimal('0.01'), mon_grouping='[3, 3, 0]',
    ...         mon_decimal_point='.')
    ...     currency.save()
    ...     CurrencyRate(date=today + relativedelta(month=1, day=1),
    ...         rate=Decimal('1.0'), currency=currency).save()
    ... else:
    ...     currency, = currencies
    >>> company.currency = currency
    >>> company_config.execute('add')
    >>> company, = Company.find()

Reload the context::

    >>> User = Model.get('res.user')
    >>> config._context = User.get_preferences(True, config.context)

Get stock locations::

    >>> Location = Model.get('stock.location')
    >>> supplier_loc, = Location.find([('code', '=', 'SUP')])
    >>> storage_loc, = Location.find([('code', '=', 'STO')])
    >>> customer_loc, = Location.find([('code', '=', 'CUS')])

Create parties::

    >>> Party = Model.get('party.party')
    >>> supplier = Party(name='Supplier')
    >>> supplier.save()
    >>> customer = Party(name='Customer')
    >>> customer.save()

Create products::

    >>> ProductUom = Model.get('product.uom')
    >>> ProductTemplate = Model.get('product.template')
    >>> kg, = ProductUom.find([('name', '=', 'Kilogram')])
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> template = ProductTemplate()
    >>> template.name = 'Product'
    >>> template.default_uom = kg
    >>> template.second_uom = unit
    >>> template.type = 'goods'
    >>> template.list_price = Decimal('300')
    >>> template.cost_price = Decimal('80')
    >>> template.cost_price_method = 'average'
    >>> template.save()
    >>> product_wo_2uom, = template.products
    >>> product_w_2uom = template.products.new()
    >>> product_w_2uom.use_second_uom = True
    >>> product_w_2uom.save()

Search by second uom::

    >>> Product = Model.get('product.product')
    >>> len(Product.find([('second_uom.code', '=', 'u')]))
    2

Receive products one month ago::

    >>> ShipmentIn = Model.get('stock.shipment.in')
    >>> shipment_in = ShipmentIn()
    >>> shipment_in.supplier = supplier
    >>> shipment_in.effective_date = last_month
    >>> incoming_move = shipment_in.incoming_moves.new()
    >>> incoming_move.product = product_wo_2uom
    >>> incoming_move.quantity = 100
    >>> incoming_move.from_location = supplier_loc
    >>> incoming_move.to_location = shipment_in.warehouse_input
    >>> incoming_move = shipment_in.incoming_moves.new()
    >>> incoming_move.product = product_w_2uom
    >>> incoming_move.quantity = 200
    >>> incoming_move.second_quantity = 10
    >>> incoming_move.from_location = supplier_loc
    >>> incoming_move.to_location = shipment_in.warehouse_input
    >>> shipment_in.save()
    >>> shipment_in.click('receive')
    >>> shipment_in.click('done')

Check available quantities::

    >>> with config.set_context({'locations': [storage_loc.id], 'stock_date_end': today}):
    ...     product_wo_2uom.reload()
    ...     product_wo_2uom.quantity
    ...     product_wo_2uom.second_quantity
    ...     product_w_2uom.reload()
    ...     product_w_2uom.quantity
    ...     product_w_2uom.second_quantity
    100.0
    0.0
    200.0
    10.0

Create an inventory::

    >>> Inventory = Model.get('stock.inventory')
    >>> inventory = Inventory()
    >>> inventory.date = last_month + relativedelta(days=5)
    >>> inventory.location = storage_loc
    >>> inventory.save()
    >>> inventory.click('complete_lines')
    >>> len(inventory.lines)
    2
    >>> for line in inventory.lines:
    ...     if line.product == product_wo_2uom:
    ...         line.expected_quantity == 100.0
    ...         line.second_expected_quantity == 0.0
    ...         line.quantity = 80.0
    ...     elif line.product == product_w_2uom:
    ...         line.expected_quantity == 200.0
    ...         line.second_expected_quantity == 10.0
    ...         line.quantity = 190.0
    ...         line.second_quantity = 8
    True
    True
    True
    True
    >>> inventory.save()
    >>> inventory.click('confirm')

Check available quantities::

    >>> with config.set_context({'locations': [storage_loc.id], 'stock_date_end': today}):
    ...     product_wo_2uom.reload()
    ...     product_wo_2uom.quantity
    ...     product_wo_2uom.second_quantity
    ...     product_w_2uom.reload()
    ...     product_w_2uom.quantity
    ...     product_w_2uom.second_quantity
    80.0
    0.0
    190.0
    8.0

Create a period::

    >>> Period = Model.get('stock.period')
    >>> period = Period()
    >>> period.date = last_month + relativedelta(days=10)
    >>> period.company = company
    >>> period.save()
    >>> period.click('close')
    >>> period.reload()
    >>> for cache in period.caches:
    ...     if (cache.product == product_wo_2uom
    ...             and cache.location == storage_loc):
    ...         cache.internal_quantity == 80.0
    ...         cache.second_internal_quantity == 0.0
    ...     elif (cache.product == product_w_2uom
    ...             and cache.location == storage_loc):
    ...         cache.internal_quantity == 190.0
    ...         cache.second_internal_quantity == 8
    True
    True
    True
    True

Check available quantities::

    >>> with config.set_context({'locations': [storage_loc.id], 'stock_date_end': today}):
    ...     product_wo_2uom.reload()
    ...     product_wo_2uom.quantity
    ...     product_wo_2uom.second_quantity
    ...     product_w_2uom.reload()
    ...     product_w_2uom.quantity
    ...     product_w_2uom.second_quantity
    80.0
    0.0
    190.0
    8.0

Create an inventory decreasing quantity in main UoM and increasing in second
UoM::

    >>> Inventory = Model.get('stock.inventory')
    >>> inventory = Inventory()
    >>> inventory.date = last_month + relativedelta(days=15)
    >>> inventory.location = storage_loc
    >>> inventory.save()
    >>> inventory.click('complete_lines')
    >>> len(inventory.lines)
    2
    >>> for line in inventory.lines:
    ...     if line.product == product_w_2uom:
    ...         line.quantity = 180.0
    ...         line.second_quantity = 9
    >>> inventory.save()
    >>> inventory.click('confirm')
    >>> inventory.reload()
    >>> inventory_move, = [m for l in inventory.lines for m in l.moves]
    >>> inventory_move.quantity
    10.0
    >>> inventory_move.second_quantity
    -1.0

Create Shipment Out::

    >>> ShipmentOut = Model.get('stock.shipment.out')
    >>> shipment_out = ShipmentOut()
    >>> shipment_out.planned_date = last_month + relativedelta(days=20)
    >>> shipment_out.effective_date = last_month + relativedelta(days=20)
    >>> shipment_out.customer = customer
    >>> outgoing_move = shipment_out.outgoing_moves.new()
    >>> outgoing_move.product = product_wo_2uom
    >>> outgoing_move.quantity = 40
    >>> outgoing_move.from_location = shipment_out.warehouse_output
    >>> outgoing_move.to_location = customer_loc
    >>> outgoing_move = shipment_out.outgoing_moves.new()
    >>> outgoing_move.product = product_w_2uom
    >>> outgoing_move.quantity = 30
    >>> outgoing_move.from_location = shipment_out.warehouse_output
    >>> outgoing_move.to_location = customer_loc
    >>> shipment_out.save()

Set the shipment state to waiting::

    >>> shipment_out.click('wait')
    >>> len(shipment_out.inventory_moves)
    2

Assign the shipment::

    >>> for inventory_move in shipment_out.inventory_moves:
    ...     if inventory_move.product == product_w_2uom:
    ...         inventory_move.second_quantity = 2
    ...         inventory_move.second_uom = unit
    >>> shipment_out.click('assign_try')
    True

.. TODO Check available quantities and forecast quantities::
.. 
..     >>> with config.set_context({'locations': [storage_loc.id], 'stock_date_end': today}):
..     ...     product_wo_2uom.reload()
..     ...     product_wo_2uom.quantity
..     ...     product_wo_2uom.second_quantity
..     ...     product_wo_2uom.forecast_quantity
..     ...     product_wo_2uom.second_forecast_quantity
..     ...     product_w_2uom.reload()
..     ...     product_w_2uom.quantity
..     ...     product_w_2uom.second_quantity
..     ...     product_w_2uom.forecast_quantity
..     ...     product_w_2uom.second_forecast_quantity
..     80.0
..     0.0
..     40.0
..     0.0
..     180.0
..     9.0
..     150.0
..     7.0

Finalize the shipment::

    >>> shipment_out.reload()
    >>> shipment_out.click('pack')
    >>> shipment_out.reload()
    >>> for outgoing_move in shipment_out.outgoing_moves:
    ...     if outgoing_move.product == product_wo_2uom:
    ...         outgoing_move.second_quantity == None
    ...     else:
    ...         outgoing_move.second_quantity == 2
    True
    True
    >>> shipment_out.click('done')

Create Shipment Out Return::

    >>> ShipmentOutReturn = Model.get('stock.shipment.out.return')
    >>> shipment_out_return = ShipmentOutReturn()
    >>> shipment_out_return.customer = customer
    >>> incoming_move = shipment_out_return.incoming_moves.new()
    >>> incoming_move.product = product_wo_2uom
    >>> incoming_move.quantity = 25
    >>> incoming_move.from_location = customer_loc
    >>> incoming_move.to_location = shipment_out_return.warehouse_input
    >>> incoming_move = shipment_out_return.incoming_moves.new()
    >>> incoming_move.product = product_w_2uom
    >>> incoming_move.quantity = 15
    >>> incoming_move.second_quantity = 1
    >>> incoming_move.from_location = customer_loc
    >>> incoming_move.to_location = shipment_out_return.warehouse_input
    >>> shipment_out_return.save()
    >>> shipment_out_return.click('receive')
    >>> shipment_out_return.click('done')

Check available quantities::

    >>> with config.set_context({'locations': [storage_loc.id], 'stock_date_end': today}):
    ...     product_wo_2uom.reload()
    ...     product_wo_2uom.quantity
    ...     product_wo_2uom.second_quantity
    ...     product_w_2uom.reload()
    ...     product_w_2uom.quantity
    ...     product_w_2uom.second_quantity
    65.0
    0.0
    165.0
    8.0

