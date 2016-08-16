<?xml version="1.0"?>
<?mso-application progid="Excel.Sheet"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:o="urn:schemas-microsoft-com:office:office"
 xmlns:x="urn:schemas-microsoft-com:office:excel"
 xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:html="http://www.w3.org/TR/REC-html40">
 <DocumentProperties xmlns="urn:schemas-microsoft-com:office:office">
  <Author>MSFUser</Author>
  <LastAuthor>MSFUser</LastAuthor>
  <Created>2012-06-18T15:46:09Z</Created>
  <Company>Medecins Sans Frontieres</Company>
  <Version>11.9999</Version>
 </DocumentProperties>
 <ExcelWorkbook xmlns="urn:schemas-microsoft-com:office:excel">
  <WindowHeight>13170</WindowHeight>
  <WindowWidth>19020</WindowWidth>
  <WindowTopX>120</WindowTopX>
  <WindowTopY>60</WindowTopY>
  <ProtectStructure>False</ProtectStructure>
  <ProtectWindows>False</ProtectWindows>
 </ExcelWorkbook>
<Styles>
    <Style ss:ID="header">
        <Alignment ss:Horizontal="Center" ss:Vertical="Center" ss:WrapText="1"/>
        <Interior ss:Color="#ffcc99" ss:Pattern="Solid"/>
        <Borders>
          <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" />
          <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" />
          <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" />
          <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" />
        </Borders>
        <Protection />
    </Style>
    <Style ss:ID="line">
        <Alignment ss:Horizontal="Center" ss:Vertical="Center" ss:WrapText="1"/>
        <Borders>
          <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" />
          <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" />
          <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" />
          <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" />
        </Borders>
        <Protection ss:Protected="0" />
    </Style>
  <Style ss:ID="short_date">
   <Alignment ss:Horizontal="Center" ss:Vertical="Center" ss:WrapText="1"/>
   <Borders>
    <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1"/>
    <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1"/>
    <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1"/>
    <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1"/>
   </Borders>
   <NumberFormat ss:Format="Short Date"/>
   <Protection ss:Protected="0" />
  </Style>
</Styles>
## ==================================== we loop over the purchase_order "objects" == purchase_order  ====================================================
% for o in objects:
<ss:Worksheet ss:Name="${"%s"%(o.name.split('/')[-1] or 'Sheet1')|x}" ss:Protected="1">
## definition of the columns' size
<% nb_of_columns = 17 %>
<Table x:FullColumns="1" x:FullRows="1">
<Column ss:AutoFitWidth="1" ss:Width="120" />
<Column ss:AutoFitWidth="1" ss:Width="300" />
% for x in range(2,nb_of_columns - 1):
<Column ss:AutoFitWidth="1" ss:Width="60" />
% endfor
<Column ss:AutoFitWidth="1" ss:Width="250" />

## we loop over the purchase_order_line "%s"%po_name.split('/')[-1])

    <Row>
        <Cell ss:StyleID="header" ><Data ss:Type="String">${_('Order Reference*')}</Data></Cell>
        <Cell ss:StyleID="line" ><Data ss:Type="String">${o.name or ''|x}</Data></Cell>
    </Row>
    <Row>
        <Cell ss:StyleID="header" ><Data ss:Type="String">${_('Order Type')}</Data></Cell>
        <Cell ss:StyleID="line" ><Data ss:Type="String">${getSel(o, 'order_type')|x}</Data></Cell>
    </Row>
    <Row>
        <Cell ss:StyleID="header" ><Data ss:Type="String">${_('Order Category')}</Data></Cell>
        <Cell ss:StyleID="line" ><Data ss:Type="String">${getSel(o, 'categ')|x}</Data></Cell>
    </Row>
    <Row>
        <Cell ss:StyleID="header" ><Data ss:Type="String">${_('Creation Date')}</Data></Cell>
        % if o.date_order not in ('False', False):
        <Cell ss:StyleID="short_date" ><Data ss:Type="DateTime">${o.date_order|n}T00:00:00.000</Data></Cell>
        % else:
        <Cell ss:StyleID="line" ><Data ss:Type="String"></Data></Cell>
        % endif
    </Row>
    <Row>
        <Cell ss:StyleID="header" ><Data ss:Type="String">${_('Supplier Reference')}</Data></Cell>
        <Cell ss:StyleID="line" ><Data ss:Type="String">${o.partner_ref or ''|x}</Data></Cell>
    </Row>
    <Row>
        <Cell ss:StyleID="header" ><Data ss:Type="String">${_('Details')}</Data></Cell>
        <Cell ss:StyleID="line" ><Data ss:Type="String">${o.details or ''|x}</Data></Cell>
    </Row>
    <Row>
        <Cell ss:StyleID="header" ><Data ss:Type="String">${_('Delivery Requested Date')}</Data></Cell>
        % if o.delivery_requested_date not in (False, 'False'):
        <Cell ss:StyleID="short_date" ><Data ss:Type="DateTime">${o.delivery_requested_date|n}T00:00:00.000</Data></Cell>
        % else:
        <Cell ss:StyleID="line" ><Data ss:Type="String"></Data></Cell>
        % endif
    </Row>
    <Row>
        <Cell ss:StyleID="header" ><Data ss:Type="String">${_('Transport mode')}</Data></Cell>
        <Cell ss:StyleID="line" ><Data ss:Type="String">${getSel(o, 'transport_type') or ''|x}</Data></Cell>
    </Row>
    <Row>
        <Cell ss:StyleID="header" ><Data ss:Type="String">${_('RTS Date')}</Data></Cell>
        % if o.ready_to_ship_date not in ('False', False):
        <Cell ss:StyleID="short_date" ><Data ss:Type="DateTime">${o.ready_to_ship_date|n}T00:00:00.000</Data></Cell>
        % else:
        <Cell ss:StyleID="line" ><Data ss:Type="String"></Data></Cell>
        % endif
    </Row>
    <Row>
        <Cell ss:StyleID="header" ><Data ss:Type="String">${_('Address name')}</Data></Cell>
        <Cell ss:StyleID="line" ><Data ss:Type="String">${o.dest_address_id and o.dest_address_id.name or ''|x}</Data></Cell>
    </Row>
    <Row>
        <Cell ss:StyleID="header" ><Data ss:Type="String">${_('Address street')}</Data></Cell>
        <Cell ss:StyleID="line" ><Data ss:Type="String">${o.dest_address_id and o.dest_address_id.street or ''|x}</Data></Cell>
    </Row>
    <Row>
        <Cell ss:StyleID="header" ><Data ss:Type="String">${_('Address street 2')}</Data></Cell>
        <Cell ss:StyleID="line" ><Data ss:Type="String">${o.dest_address_id and o.dest_address_id.street2 or ''|x}</Data></Cell>
    </Row>
    <Row>
        <Cell ss:StyleID="header" ><Data ss:Type="String">${_('Zip')}</Data></Cell>
        <Cell ss:StyleID="line" ><Data ss:Type="String">${o.dest_address_id and o.dest_address_id.zip or ''|x}</Data></Cell>
    </Row>
    <Row>
        <Cell ss:StyleID="header" ><Data ss:Type="String">${_('City')}</Data></Cell>
        <Cell ss:StyleID="line" ><Data ss:Type="String">${o.dest_address_id and o.dest_address_id.city or ''|x}</Data></Cell>
    </Row>
    <Row>
        <Cell ss:StyleID="header" ><Data ss:Type="String">${_('Country')}</Data></Cell>
        <Cell ss:StyleID="line" ><Data ss:Type="String">${o.dest_address_id and o.dest_address_id.country_id and o.dest_address_id.country_id.name or ''|x}</Data></Cell>
    </Row>
    <Row>
        <Cell ss:StyleID="header" ><Data ss:Type="String">${_('Shipment Date')}</Data></Cell>
        % if o.shipment_date not in ('False', False):
        <Cell ss:StyleID="short_date" ><Data ss:Type="DateTime">${o.shipment_date|n}T00:00:00.000</Data></Cell>
        % else:
        <Cell ss:StyleID="line" ><Data ss:Type="String"></Data></Cell>
        % endif
    </Row>
    <Row>
        <Cell ss:StyleID="header" ><Data ss:Type="String">${_('Notes')}</Data></Cell>
        <Cell ss:StyleID="line" ><Data ss:Type="String">${o.notes or ''|x}</Data></Cell>
    </Row>
    <Row>
        <Cell ss:StyleID="header" ><Data ss:Type="String">${_('Origin')}</Data></Cell>
        <Cell ss:StyleID="line" ><Data ss:Type="String">${o.origin or ''|x}</Data></Cell>
    </Row>
    <Row>
        <Cell ss:StyleID="header" ><Data ss:Type="String">${_('Project Ref.')}</Data></Cell>
        <Cell ss:StyleID="line" ><Data ss:Type="String">${o.fnct_project_ref or ''|x}</Data></Cell>
    </Row>
    <Row>
        <Cell ss:StyleID="header" ><Data ss:Type="String">${_('Message ESC Header')}</Data></Cell>
        <Cell ss:StyleID="line" ><Data ss:Type="String">${o.message_esc or ''|x}</Data></Cell>
    </Row>
    
    <Row>
        <Cell ss:StyleID="header" ><Data ss:Type="String">${_('Line number')}</Data></Cell>    
        <Cell ss:StyleID="header" ><Data ss:Type="String">${_('Ext. Ref.')}</Data></Cell>    
        <Cell ss:StyleID="header" ><Data ss:Type="String">${_('Product Code*')}</Data></Cell>
        <Cell ss:StyleID="header" ><Data ss:Type="String">${_('Product Description')}</Data></Cell>
        <Cell ss:StyleID="header" ><Data ss:Type="String">${_('Product Qty*')}</Data></Cell>
        <Cell ss:StyleID="header" ><Data ss:Type="String">${_('Product UoM*')}</Data></Cell>
        <Cell ss:StyleID="header" ><Data ss:Type="String">${_('Price Unit*')}</Data></Cell>
        <Cell ss:StyleID="header" ><Data ss:Type="String">${_('Currency*')}</Data></Cell>
        <Cell ss:StyleID="header" ><Data ss:Type="String">${_('Origin*')}</Data></Cell>
        <Cell ss:StyleID="header" ><Data ss:Type="String">${_('Delivery requested date')}</Data></Cell>
        <Cell ss:StyleID="header" ><Data ss:Type="String">${_('Delivery confirmed date*')}</Data></Cell>
        <Cell ss:StyleID="header" ><Data ss:Type="String">${_('Nomen Name')}</Data></Cell>
        <Cell ss:StyleID="header" ><Data ss:Type="String">${_('Nomen Group')}</Data></Cell>
        <Cell ss:StyleID="header" ><Data ss:Type="String">${_('Nomen Family')}</Data></Cell>
        <Cell ss:StyleID="header" ><Data ss:Type="String">${_('Comment')}</Data></Cell>
        <Cell ss:StyleID="header" ><Data ss:Type="String">${_('Notes')}</Data></Cell>
        <Cell ss:StyleID="header" ><Data ss:Type="String">${_('Project Ref')}</Data></Cell>
        <Cell ss:StyleID="header" ><Data ss:Type="String">${_('ESC Message 1')}</Data></Cell>
        <Cell ss:StyleID="header" ><Data ss:Type="String">${_('ESC Message 2')}</Data></Cell>
    </Row>
    % for line in o.order_line:
    <Row>
        <Cell ss:StyleID="line" ><Data ss:Type="String">${(line.line_number or '')|x}</Data></Cell>
        <Cell ss:StyleID="line" ><Data ss:Type="String">${(line.external_ref or '')|x}</Data></Cell>
        <Cell ss:StyleID="line" ><Data ss:Type="String">${(line.product_id and line.product_id.default_code or '')|x}</Data></Cell>
        <Cell ss:StyleID="line" ><Data ss:Type="String">${(line.product_id and line.product_id.name or '')|x}</Data></Cell>
        <Cell ss:StyleID="line" ><Data ss:Type="Number">${(line.product_qty or 0.00)|x}</Data></Cell>
        <Cell ss:StyleID="line" ><Data ss:Type="String">${(line.product_uom.name or '')|x}</Data></Cell>
        <Cell ss:StyleID="line" ><Data ss:Type="Number">${(line.price_unit or 0.00)|x}</Data></Cell>
        <Cell ss:StyleID="line" ><Data ss:Type="String">${(o.pricelist_id.currency_id.name or '')|x}</Data></Cell>
        <Cell ss:StyleID="line" ><Data ss:Type="String">${(line.origin or '')|x}</Data></Cell>
        % if line.date_planned not in (False, 'False'):
        <Cell ss:StyleID="short_date" ><Data ss:Type="DateTime">${line.date_planned|n}T00:00:00.000</Data></Cell>
        % elif o.delivery_requested_date not in (False, 'False'):
        ## if the date does not exist in the line we take the one from the header
        <Cell ss:StyleID="short_date" ><Data ss:Type="DateTime">${o.delivery_requested_date|n}T00:00:00.000</Data></Cell>
        % else:
        <Cell ss:StyleID="line" ><Data ss:Type="String"></Data></Cell>
        % endif
        % if line.confirmed_delivery_date not in ('False', False):
        <Cell ss:StyleID="short_date" ><Data ss:Type="DateTime">${line.confirmed_delivery_date|n}T00:00:00.000</Data></Cell>
        % elif o.delivery_confirmed_date not in ('False', False):
        ## if the date does not exist in the line we take the one from the header
        <Cell ss:StyleID="short_date" ><Data ss:Type="DateTime">${o.delivery_confirmed_date|n}T00:00:00.000</Data></Cell>
        % else:
        <Cell ss:StyleID="line" ><Data ss:Type="String"></Data></Cell>
        % endif
        <Cell ss:StyleID="line" ><Data ss:Type="String">${(line.nomen_manda_0 and line.nomen_manda_0.name or '')|x}</Data></Cell>
        <Cell ss:StyleID="line" ><Data ss:Type="String">${(line.nomen_manda_1 and line.nomen_manda_1.name or '')|x}</Data></Cell>
        <Cell ss:StyleID="line" ><Data ss:Type="String">${(line.nomen_manda_2 and line.nomen_manda_2.name or '')|x}</Data></Cell>
        <Cell ss:StyleID="line" ><Data ss:Type="String">${(line.comment or '')|x}</Data></Cell>
        <Cell ss:StyleID="line" ><Data ss:Type="String">${(line.notes or '')|x}</Data></Cell>
        <Cell ss:StyleID="line" ><Data ss:Type="String">${(line.fnct_project_ref or '')|x}</Data></Cell>
        <Cell ss:StyleID="line" ><Data ss:Type="String"></Data></Cell>
        <Cell ss:StyleID="line" ><Data ss:Type="String"></Data></Cell>
    </Row>
    % endfor
</Table>
<x:WorksheetOptions xmlns="urn:schemas-microsoft-com:office:excel">
    <ProtectObjects>True</ProtectObjects>
    <ProtectScenarios>True</ProtectScenarios>
    <EnableSelection>UnlockedCells</EnableSelection>
    <AllowInsertRows />
</x:WorksheetOptions>
</ss:Worksheet>
% endfor
</Workbook>
