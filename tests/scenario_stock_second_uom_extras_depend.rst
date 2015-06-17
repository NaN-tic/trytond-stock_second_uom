=======================================
Second UoM Scenario with extras depends
=======================================

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

Install product_raw_variant Module::

    >>> Module = Model.get('ir.module.module')
    >>> stock_module, = Module.find([('name', '=', 'product_raw_variant')])
    >>> stock_module.click('install')
    >>> Wizard('ir.module.module.install_upgrade').execute('upgrade')

Install stock_lot Module::

    >>> Module = Model.get('ir.module.module')
    >>> stock_module, = Module.find([('name', '=', 'stock_lot')])
    >>> stock_module.click('install')
    >>> Wizard('ir.module.module.install_upgrade').execute('upgrade')

Install sale Module::

    >>> Module = Model.get('ir.module.module')
    >>> stock_module, = Module.find([('name', '=', 'sale')])
    >>> stock_module.click('install')
    >>> Wizard('ir.module.module.install_upgrade').execute('upgrade')

Install purchase Module::

    >>> Module = Model.get('ir.module.module')
    >>> stock_module, = Module.find([('name', '=', 'purchase')])
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

Create fiscal year::

    >>> FiscalYear = Model.get('account.fiscalyear')
    >>> Sequence = Model.get('ir.sequence')
    >>> SequenceStrict = Model.get('ir.sequence.strict')
    >>> fiscalyear = FiscalYear(name=str(today.year))
    >>> fiscalyear.start_date = today + relativedelta(month=1, day=1)
    >>> fiscalyear.end_date = today + relativedelta(month=12, day=31)
    >>> fiscalyear.company = company
    >>> post_move_seq = Sequence(name=str(today.year), code='account.move',
    ...     company=company)
    >>> post_move_seq.save()
    >>> fiscalyear.post_move_sequence = post_move_seq
    >>> invoice_seq = SequenceStrict(name=str(today.year),
    ...     code='account.invoice', company=company)
    >>> invoice_seq.save()
    >>> fiscalyear.out_invoice_sequence = invoice_seq
    >>> fiscalyear.in_invoice_sequence = invoice_seq
    >>> fiscalyear.out_credit_note_sequence = invoice_seq
    >>> fiscalyear.in_credit_note_sequence = invoice_seq
    >>> fiscalyear.save()
    >>> FiscalYear.create_period([fiscalyear.id], config.context)

Create chart of accounts::

    >>> AccountTemplate = Model.get('account.account.template')
    >>> Account = Model.get('account.account')
    >>> Journal = Model.get('account.journal')
    >>> account_template, = AccountTemplate.find([('parent', '=', None)])
    >>> create_chart = Wizard('account.create_chart')
    >>> create_chart.execute('account')
    >>> create_chart.form.account_template = account_template
    >>> create_chart.form.company = company
    >>> create_chart.execute('create_account')
    >>> receivable, = Account.find([
    ...         ('kind', '=', 'receivable'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> payable, = Account.find([
    ...         ('kind', '=', 'payable'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> revenue, = Account.find([
    ...         ('kind', '=', 'revenue'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> expense, = Account.find([
    ...         ('kind', '=', 'expense'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> create_chart.form.account_receivable = receivable
    >>> create_chart.form.account_payable = payable
    >>> create_chart.execute('create_properties')
    >>> cash, = Account.find([
    ...         ('kind', '=', 'other'),
    ...         ('name', '=', 'Main Cash'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> cash_journal, = Journal.find([('type', '=', 'cash')])
    >>> cash_journal.credit_account = cash
    >>> cash_journal.debit_account = cash
    >>> cash_journal.save()

Create payment term::

    >>> PaymentTerm = Model.get('account.invoice.payment_term')
    >>> PaymentTermLine = Model.get('account.invoice.payment_term.line')
    >>> payment_term = PaymentTerm(name='Direct')
    >>> payment_term_line = PaymentTermLine(type='remainder', days=0)
    >>> payment_term.lines.append(payment_term_line)
    >>> payment_term.save()

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
    >>> template.purchasable = True
    >>> template.salable = True
    >>> template.list_price = Decimal('300')
    >>> template.cost_price = Decimal('80')
    >>> template.cost_price_method = 'average'
    >>> template.account_expense = expense
    >>> template.account_revenue = revenue
    >>> template.save()
    >>> product_wo_2uom, = template.products
    >>> product_w_2uom = template.products.new()
    >>> product_w_2uom.use_second_uom = True
    >>> product_w_2uom.save()

    >>> LotType = Model.get('stock.lot.type')
    >>> template = ProductTemplate()
    >>> template.name = 'Product'
    >>> template.default_uom = kg
    >>> template.second_uom = unit
    >>> template.type = 'goods'
    >>> template.purchasable = True
    >>> template.salable = True
    >>> template.list_price = Decimal('300')
    >>> template.cost_price = Decimal('80')
    >>> template.cost_price_method = 'average'
    >>> template.account_expense = expense
    >>> template.account_revenue = revenue
    >>> for lot_type in LotType.find([]):
    ...     template.lot_required.append(lot_type)
    >>> template.save()
    >>> product_lot_wo_2uom, = template.products
    >>> product_lot_w_2uom = template.products.new()
    >>> product_lot_w_2uom.use_second_uom = True
    >>> product_lot_w_2uom.save()

Purchase products two month ago::

    >>> Purchase = Model.get('purchase.purchase')
    >>> purchase = Purchase()
    >>> purchase.party = supplier
    >>> purchase.date = last_month - relativedelta(months=1)
    >>> purchase.payment_term = payment_term
    >>> purchase.invoice_method = 'manual'
    >>> purchase_line = purchase.lines.new()
    >>> purchase_line.product = product_wo_2uom
    >>> purchase_line.quantity = 100
    >>> purchase_line = purchase.lines.new()
    >>> purchase_line.product = product_w_2uom
    >>> purchase_line.quantity = 200
    >>> purchase_line.second_quantity = 10
    >>> purchase_line = purchase.lines.new()
    >>> purchase_line.product = product_lot_wo_2uom
    >>> purchase_line.quantity = 25
    >>> purchase_line = purchase.lines.new()
    >>> purchase_line.product = product_lot_w_2uom
    >>> purchase_line.quantity = 75
    >>> purchase_line.second_quantity = 6
    >>> purchase.click('quote')
    >>> purchase.click('confirm')
    >>> purchase.click('process')
    >>> purchase.state
    u'processing'
    >>> len(purchase.moves), len(purchase.shipment_returns)
    (4, 0)
    >>> for move in purchase.moves:
    ...     if move.product in (product_wo_2uom, product_lot_wo_2uom):
    ...         (move.second_uom == None, move.second_quantity == None)
    ...     elif move.product == product_w_2uom:
    ...         (move.second_uom == unit, move.second_quantity == 10)
    ...     elif move.product == product_lot_w_2uom:
    ...         (move.second_uom == unit, move.second_quantity == 6)
    (True, True)
    (True, True)
    (True, True)
    (True, True)

Validate Shipments one month ago::

    >>> ShipmentIn = Model.get('stock.shipment.in')
    >>> Move = Model.get('stock.move')
    >>> Lot = Model.get('stock.lot')
    >>> shipment_in = ShipmentIn()
    >>> shipment_in.supplier = supplier
    >>> shipment_in.effective_date = last_month
    >>> for move in purchase.moves:
    ...     incoming_move = Move(id=move.id)
    ...     if move.product == product_lot_wo_2uom:
    ...         lot_wo_2uom = Lot(
    ...             product=product_lot_wo_2uom,
    ...             number=str(product_lot_wo_2uom.id))
    ...         lot_wo_2uom.save()
    ...         incoming_move.lot = lot_wo_2uom
    ...     elif move.product == product_lot_w_2uom:
    ...         lot_w_2uom = Lot(
    ...             product=product_lot_w_2uom,
    ...             number=str(product_lot_wo_2uom.id))
    ...         lot_w_2uom.save()
    ...         incoming_move.lot = lot_w_2uom
    ...     shipment_in.incoming_moves.append(incoming_move)
    >>> shipment_in.save()
    >>> shipment_in.click('receive')
    >>> shipment_in.click('done')

Check available quantities by product::

    >>> with config.set_context({'locations': [storage_loc.id], 'stock_date_end': today}):
    ...     product_wo_2uom.reload()
    ...     product_wo_2uom.quantity
    ...     product_wo_2uom.second_quantity
    ...     product_w_2uom.reload()
    ...     product_w_2uom.quantity
    ...     product_w_2uom.second_quantity
    ...     product_lot_wo_2uom.reload()
    ...     product_lot_wo_2uom.quantity
    ...     product_lot_wo_2uom.second_quantity
    ...     product_lot_w_2uom.reload()
    ...     product_lot_w_2uom.quantity
    ...     product_lot_w_2uom.second_quantity
    100.0
    0.0
    200.0
    10.0
    25.0
    0.0
    75.0
    6.0

Check available quantities by lot::

    >>> with config.set_context({'locations': [storage_loc.id], 'stock_date_end': today}):
    ...     lot_wo_2uom.reload()
    ...     lot_wo_2uom.quantity
    ...     lot_wo_2uom.second_quantity
    ...     lot_w_2uom.reload()
    ...     lot_w_2uom.quantity
    ...     lot_w_2uom.second_quantity
    25.0
    0.0
    75.0
    6.0

Create an inventory::

    >>> Inventory = Model.get('stock.inventory')
    >>> inventory = Inventory()
    >>> inventory.date = last_month + relativedelta(days=5)
    >>> inventory.location = storage_loc
    >>> inventory.save()
    >>> inventory.click('complete_lines')
    >>> len(inventory.lines)
    4
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
    ...     elif line.product == product_lot_wo_2uom and line.lot == lot_wo_2uom:
    ...         line.expected_quantity == 25.0
    ...         line.second_expected_quantity == 0.0
    ...         line.quantity = 30.0
    ...     elif line.product == product_lot_w_2uom and line.lot == lot_w_2uom:
    ...         line.expected_quantity == 75.0
    ...         line.second_expected_quantity == 6.0
    ...         line.quantity = 85.0
    ...         line.second_quantity = 7
    True
    True
    True
    True
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
    ...     product_lot_wo_2uom.reload()
    ...     product_lot_wo_2uom.quantity
    ...     product_lot_wo_2uom.second_quantity
    ...     product_lot_w_2uom.reload()
    ...     product_lot_w_2uom.quantity
    ...     product_lot_w_2uom.second_quantity
    ...     lot_wo_2uom.reload()
    ...     lot_wo_2uom.quantity
    ...     lot_wo_2uom.second_quantity
    ...     lot_w_2uom.reload()
    ...     lot_w_2uom.quantity
    ...     lot_w_2uom.second_quantity
    80.0
    0.0
    190.0
    8.0
    30.0
    0.0
    85.0
    7.0
    30.0
    0.0
    85.0
    7.0

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
    ...     elif (cache.product == product_lot_wo_2uom
    ...             and cache.location == storage_loc):
    ...         cache.internal_quantity == 30.0
    ...         cache.second_internal_quantity == 0.0
    ...     elif (cache.product == product_lot_w_2uom
    ...             and cache.location == storage_loc):
    ...         cache.internal_quantity == 85.0
    ...         cache.second_internal_quantity == 7
    True
    True
    True
    True
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
    ...     product_lot_wo_2uom.reload()
    ...     product_lot_wo_2uom.quantity
    ...     product_lot_wo_2uom.second_quantity
    ...     product_lot_w_2uom.reload()
    ...     product_lot_w_2uom.quantity
    ...     product_lot_w_2uom.second_quantity
    ...     lot_wo_2uom.reload()
    ...     lot_wo_2uom.quantity
    ...     lot_wo_2uom.second_quantity
    ...     lot_w_2uom.reload()
    ...     lot_w_2uom.quantity
    ...     lot_w_2uom.second_quantity
    80.0
    0.0
    190.0
    8.0
    30.0
    0.0
    85.0
    7.0
    30.0
    0.0
    85.0
    7.0

Create an inventory decreasing quantity in main UoM and increasing in second
UoM::

    >>> Inventory = Model.get('stock.inventory')
    >>> inventory = Inventory()
    >>> inventory.date = last_month + relativedelta(days=15)
    >>> inventory.location = storage_loc
    >>> inventory.save()
    >>> inventory.click('complete_lines')
    >>> len(inventory.lines)
    4
    >>> for line in inventory.lines:
    ...     if line.product == product_w_2uom:
    ...         line.quantity = 180.0
    ...         line.second_quantity = 9
    ...     elif line.product == product_lot_w_2uom:
    ...         line.quantity = 90.0
    ...         line.second_quantity = 5
    >>> inventory.save()
    >>> inventory.click('confirm')
    >>> inventory.reload()
    >>> inventory_moves = [m for l in inventory.lines for m in l.moves]
    >>> len(inventory_moves)
    2
    >>> for move in inventory_moves:
    ...     if move.product == product_w_2uom:
    ...         move.quantity == 10.0
    ...         move.second_quantity == -1.0
    ...     elif move.product == product_lot_w_2uom:
    ...         move.quantity == 5.0
    ...         move.second_quantity == -2.0
    True
    True
    True
    True

Sale products::

    >>> Sale = Model.get('sale.sale')
    >>> sale = Sale()
    >>> sale.party = customer
    >>> sale.date = last_month + relativedelta(days=18)
    >>> sale.payment_term = payment_term
    >>> sale.invoice_method = 'manual'
    >>> sale_line = sale.lines.new()
    >>> sale_line.product = product_wo_2uom
    >>> sale_line.quantity = 40.0
    >>> sale_line = sale.lines.new()
    >>> sale_line.product = product_w_2uom
    >>> sale_line.quantity = 30.0
    >>> sale_line.second_quantity = 2
    >>> sale_line = sale.lines.new()
    >>> sale_line.product = product_lot_wo_2uom
    >>> sale_line.quantity = 10.0
    >>> sale_line = sale.lines.new()
    >>> sale_line.product = product_lot_w_2uom
    >>> sale_line.quantity = 80.0
    >>> sale_line.second_quantity = 4
    >>> sale.save()
    >>> Sale.quote([sale.id], config.context)
    >>> Sale.confirm([sale.id], config.context)
    >>> Sale.process([sale.id], config.context)
    >>> sale.state
    u'processing'
    >>> sale.reload()
    >>> len(sale.shipments), len(sale.shipment_returns), len(sale.moves)
    (1, 0, 4)
    >>> for move in sale.moves:
    ...     if move.product in (product_wo_2uom, product_lot_wo_2uom):
    ...         move.second_uom == None and move.second_quantity == None
    ...     elif move.product == product_w_2uom:
    ...         move.second_uom == unit and move.second_quantity == 2
    ...     elif move.product == product_lot_w_2uom:
    ...         move.second_uom == unit and move.second_quantity == 4
    True
    True
    True
    True

Check sale shpiment inventory moves::

    >>> shipment_out, = sale.shipments
    >>> len(shipment_out.inventory_moves)
    4
    >>> for move in shipment_out.inventory_moves:
    ...     if move.product == product_wo_2uom:
    ...         (move.second_uom == None, move.second_quantity == None)
    ...     elif move.product == product_w_2uom:
    ...         (move.second_uom == unit, move.second_quantity == 2)
    ...     elif move.product == product_lot_wo_2uom:
    ...         (move.second_uom == None, move.second_quantity == None)
    ...         move.lot = lot_wo_2uom
    ...     elif move.product == product_lot_w_2uom:
    ...         (move.second_uom == unit, move.second_quantity == 4)
    ...         move.lot = lot_w_2uom
    (True, True)
    (True, True)
    (True, True)
    (True, True)
    >>> shipment_out.save()

Assign sale shipment::

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
..     ...     product_lot_wo_2uom.reload()
..     ...     product_lot_wo_2uom.quantity
..     ...     product_lot_wo_2uom.second_quantity
..     ...     product_lot_wo_2uom.forecast_quantity
..     ...     product_lot_wo_2uom.second_forecast_quantity
..     ...     product_lot_w_2uom.reload()
..     ...     product_lot_w_2uom.quantity
..     ...     product_lot_w_2uom.second_quantity
..     ...     product_lot_w_2uom.forecast_quantity
..     ...     product_lot_w_2uom.second_forecast_quantity
..     ...     lot_wo_2uom.reload()
..     ...     lot_wo_2uom.quantity
..     ...     lot_wo_2uom.second_quantity
..     ...     lot_wo_2uom.forecast_quantity
..     ...     lot_wo_2uom.second_forecast_quantity
..     ...     lot_w_2uom.reload()
..     ...     lot_w_2uom.quantity
..     ...     lot_w_2uom.second_quantity
..     ...     lot_w_2uom.forecast_quantity
..     ...     lot_w_2uom.second_forecast_quantity
..     80.0
..     0.0
..     40.0
..     0.0
..     180.0
..     9.0
..     150.0
..     7.0
..     30.0
..     0.0
..     20.0
..     0.0
..     90.0
..     5.0
..     10.0
..     1.0
..     30.0
..     0.0
..     20.0
..     0.0
..     90.0
..     5.0
..     10.0
..     1.0

Finalize the shipment::

    >>> shipment_out.reload()
    >>> shipment_out.click('pack')
    >>> shipment_out.reload()
    >>> shipment_out.click('done')

Create return sale::

    >>> return_sale = Wizard('sale.return_sale', [sale])
    >>> return_sale.execute('return_')
    >>> returned_sale, = Sale.find([
    ...     ('state', '=', 'draft'),
    ...     ])
    >>> sorted([(x.quantity, x.second_quantity) for x in returned_sale.lines])
    [(-80.0, -4.0), (-40.0, None), (-30.0, -2.0), (-10.0, None)]
    >>> for sale_line in returned_sale.lines:
    ...     if sale_line.product == product_wo_2uom:
    ...         sale_line.quantity = -25
    ...     elif sale_line.product == product_w_2uom:
    ...         sale_line.quantity = -15
    ...         sale_line.second_quantity = -1
    ...     elif sale_line.product == product_lot_wo_2uom:
    ...         sale_line.quantity = -2
    ...     elif sale_line.product == product_lot_w_2uom:
    ...         sale_line.quantity = -10
    ...         sale_line.second_quantity = -1
    >>> returned_sale.save()
    >>> returned_sale.click('quote')
    >>> returned_sale.click('confirm')
    >>> returned_sale.click('process')
    >>> returned_sale.state
    u'processing'
    >>> len(returned_sale.shipments), len(returned_sale.shipment_returns)
    (0, 1)

Validate return shipment::

    >>> shipment_return, = returned_sale.shipment_returns
    >>> for move in shipment_return.incoming_moves:
    ...     if move.product == product_wo_2uom:
    ...        move.second_quantity == None
    ...     elif move.product == product_w_2uom:
    ...        move.second_quantity == 1
    ...     elif move.product == product_lot_wo_2uom:
    ...         move.second_quantity == None
    ...         move.lot = lot_wo_2uom
    ...     elif move.product == product_lot_w_2uom:
    ...         move.second_quantity == 1
    ...         move.lot = lot_w_2uom
    True
    True
    True
    True
    >>> shipment_return.save()
    >>> shipment_return.click('receive')
    >>> shipment_return.click('done')

Check available quantities::

    >>> with config.set_context({'locations': [storage_loc.id], 'stock_date_end': today}):
    ...     product_wo_2uom.reload()
    ...     product_wo_2uom.quantity
    ...     product_wo_2uom.second_quantity
    ...     product_w_2uom.reload()
    ...     product_w_2uom.quantity
    ...     product_w_2uom.second_quantity
    ...     product_lot_wo_2uom.reload()
    ...     product_lot_wo_2uom.quantity
    ...     product_lot_wo_2uom.second_quantity
    ...     product_lot_w_2uom.reload()
    ...     product_lot_w_2uom.quantity
    ...     product_lot_w_2uom.second_quantity
    ...     lot_wo_2uom.reload()
    ...     lot_wo_2uom.quantity
    ...     lot_wo_2uom.second_quantity
    ...     lot_w_2uom.reload()
    ...     lot_w_2uom.quantity
    ...     lot_w_2uom.second_quantity
    65.0
    0.0
    165.0
    8.0
    22.0
    0.0
    20.0
    2.0
    22.0
    0.0
    20.0
    2.0

