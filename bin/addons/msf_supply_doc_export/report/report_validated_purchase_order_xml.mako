<?xml version="1.0"?>
<data>
% for o in objects:
    <record model="purchase.order" key="name">
        <field name="name">${o.name or ''|x}</field>
        <field name="order_type">${getSel(o, 'order_type')|x}</field>
        <field name="categ">${getSel(o, 'categ')|x}</field>
        % if o.date_order and o.date_order not in (False, 'False'):
            <field name="date_order">${o.date_order|n}</field>
        % else:
            <field name="date_order"></field>
        % endif
        <field name="partner_ref">${o.partner_ref or ''|x}</field>
        <field name="details">${o.details or ''|x}</field>
        % if o.delivery_requested_date and o.delivery_requested_date not in (False, 'False'):
        <field name="delivery_requested_date">${o.delivery_requested_date or ''|n}</field>
        % else:
        <field name="delivery_requested_date"></field>
        % endif
        <field name="transport_type">${getSel(o, 'transport_type') or ''|x}</field>
        % if o.ready_to_ship_date and o.ready_to_ship_date not in (False, 'False'):
        <field name="ready_to_ship_date">${o.ready_to_ship_date|n}</field>
        % else:
        <field name="ready_to_ship_date"></field>
        % endif
        <field name="dest_address_id" key="name,parent.partner_id">
        <field name="name">${o.dest_address_id and o.dest_address_id.name or ''|x}</field>
        <field name="street">${o.dest_address_id and o.dest_address_id.street or ''|x}</field>
        <field name="street2">${o.dest_address_id and o.dest_address_id.street2 or ''|x}</field>
        <field name="zip">${o.dest_address_id and o.dest_address_id.zip or ''|x}</field>
        <field name="city">${o.dest_address_id and o.dest_address_id.city or ''|x}</field>
        <field name="country_id" key="name">
            <field name="name">${o.dest_address_id and o.dest_address_id.country_id and o.dest_address_id.country_id.name or ''|x}</field>
        </field>
        </field>
        % if o.shipment_date and o.shipment_date not in (False, 'False'):
        <field name="shipment_date">${o.shipment_date|n}</field>
        % else:
        <field name="shipment_date"></field>
        % endif
        <field name="notes">${o.notes or ''|x}</field>
        <field name="origin">${o.origin or ''|x}</field>
        <field name="project_ref">${o.fnct_project_ref or ''|x}</field>
        <field name="message_esc">${o.message_esc or ''|x}</field>
        <field name="order_line">
        % for l in o.order_line:
            <record>
                <field name="line_number">${l.line_number or ''|x}</field>
                <field name="external_ref">${l.external_ref or ''|x}</field>
                <field name="product_id" key="default_code,name">
                    <field name="product_code">${l.product_id and l.product_id.default_code or ''|x}</field>
                    <field name="product_name">${l.product_id and l.product_id.name or ''|x}</field>
                </field>
                <field name="product_qty">${l.product_qty or 0.00}</field>
                <field name="product_uom" key="name">
                    <field name="name">${l.product_uom and l.product_uom.name or ''|x}</field>
                </field>
                <field name="price_unit">${l.price_unit or ''}</field>
                <field name="currency_id" key="name">
                    <field name="name">${l.currency_id and l.currency_id.name or ''|x}</field>
                </field>
                <field name="origin">${l.origin or ''|x}</field>
                % if l.date_planned and l.date_planned not in (False, 'False'):
                <field name="date_planned">${l.date_planned|n}</field>
                % else:
                <field name="date_planned"></field>
                % endif
                % if l.confirmed_delivery_date and l.confirmed_delivery_date not in (False, 'False'):
                <field name="confirmed_delivery_date">${l.confirmed_delivery_date|n}</field>
                % else:
                <field name="confirmed_delivery_date"></field>
                % endif
                <field name="nomen_manda_0" key="name">
                    <field name="name">${l.nomen_manda_0 and l.nomen_manda_0.name or ''|x}</field>
                </field>
                <field name="nomen_manda_1" key="name">
                    <field name="name">${l.nomen_manda_1 and l.nomen_manda_1.name or ''|x}</field>
                </field>
                <field name="nomen_manda_2" key="name">
                    <field name="name">${l.nomen_manda_2 and l.nomen_manda_2.name or ''|x}</field>
                </field>
                <field name="comment">${l.comment or ''|x}</field>
                <field name="notes">${l.notes or ''|x}</field>
                <field name="project_ref">${l.fnct_project_ref or ''|x}</field>
                <field name="message_esc1"></field>
                <field name="message_esc2"></field>
            </record>
        % endfor
        </field>
    </record>
    % endfor
</data>
