<?xml version="1.0"?>
<?mso-application progid="Excel.Sheet"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:o="urn:schemas-microsoft-com:office:office"
 xmlns:x="urn:schemas-microsoft-com:office:excel"
 xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:html="http://www.w3.org/TR/REC-html40">
 <DocumentProperties xmlns="urn:schemas-microsoft-com:office:office">
  <Author>Unifield</Author>
  <LastAuthor>MSFUser</LastAuthor>
  <Created>2014-04-16T22:36:07Z</Created>
  <Company>Medecins Sans Frontieres</Company>
  <Version>11.9999</Version>
 </DocumentProperties>
 <ExcelWorkbook xmlns="urn:schemas-microsoft-com:office:excel">
  <WindowHeight>11640</WindowHeight>
  <WindowWidth>15480</WindowWidth>
  <WindowTopX>120</WindowTopX>
  <WindowTopY>75</WindowTopY>
  <ProtectStructure>False</ProtectStructure>
  <ProtectWindows>False</ProtectWindows>
 </ExcelWorkbook>
 <Styles>
    <Style ss:ID="ssCell">
        <Alignment ss:Vertical="Top" ss:WrapText="1"/>
        <Font ss:Bold="1" />
    </Style>
    <Style ss:ID="ssCellBlue">
        <Alignment ss:Vertical="Top" ss:WrapText="1"/>
        <Font ss:Color="#0000FF" />
    </Style>

    <!-- File header -->
    <Style ss:ID="big_header">
        <Font x:Family="Swiss" ss:Size="14" ss:Bold="1"/>
    </Style>
    <Style ss:ID="file_header">
        <Font ss:Size="9" />
        <Interior ss:Color="#C0C0C0" ss:Pattern="Solid"/>
    </Style>

    <!-- Line header -->
    <Style ss:ID="line_header">
        <Borders>
            <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1"/>
            <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1"/>
            <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1"/>
            <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1"/>
        </Borders>
        <Font x:Family="Swiss" ss:Size="7" ss:Bold="1"/>
        <Interior/>
    </Style>

    <!-- Lines -->
    <Style ss:ID="line_left">
        <Alignment ss:Horizontal="Left" ss:Vertical="Bottom"/>
        <Borders>
            <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1"/>
            <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1"/>
            <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1"/>
            <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1"/>
        </Borders>
        <Font ss:Size="8" ss:Color="#0000FF"/>
    </Style>
    <Style ss:ID="line_right">
        <Alignment ss:Horizontal="Right" ss:Vertical="Bottom"/>
        <Borders>
            <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1"/>
            <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1"/>
            <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1"/>
            <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1"/>
        </Borders>
        <Font ss:Size="8" ss:Color="#0000FF"/>
        <NumberFormat ss:Format="#,##0.00"/>
    </Style>
     <Style ss:ID="line_center">
        <Alignment ss:Horizontal="Center" ss:Vertical="Bottom"/>
         <Borders>
            <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1"/>
            <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1"/>
            <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1"/>
            <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1"/>
        </Borders>
        <Font ss:Size="8" ss:Color="#0000FF"/>
        <NumberFormat ss:Format="#,##0.00"/>
    </Style>
    <Style ss:ID="line_left_date">
        <Alignment ss:Horizontal="Right" ss:Vertical="Bottom"/>
        <NumberFormat ss:Format="Short Date" />
        <Borders>
            <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1"/>
            <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1"/>
            <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1"/>
            <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1"/>
        </Borders>
        <Font ss:Size="8" ss:Color="#0000FF"/>
    </Style>

    <Style ss:ID="short_date">
        <Alignment ss:Horizontal="Left" ss:Vertical="Center" ss:WrapText="1" />
        <NumberFormat ss:Format="Short Date" />
        <Font ss:Color="#0000FF" />
    </Style>
</Styles>


% for r in objects:
<ss:Worksheet ss:Name="FO Follow Up">
    <Table x:FullColumns="1" x:FullRows="1">
        ## Order ref
        <Column ss:AutoFitWidth="1" ss:Width="130.0" />
        ## Customer ref
        <Column ss:AutoFitWidth="1" ss:Width="170.0" />
        ## PO ref
        <Column ss:AutoFitWidth="1" ss:Width="150.0" />
        ## Status
        <Column ss:AutoFitWidth="1" ss:Width="60.75" />
        ## Received
        <Column ss:AutoFitWidth="1" ss:Width="54.75" />
        ## Requested Delivery Date
        <Column ss:AutoFitWidth="1" ss:Width="54.75" />
        ## order line
        <Column ss:AutoFitWidth="1" ss:Width="19.00" />
        ## product code
        <Column ss:AutoFitWidth="1" ss:Width="107.25" />
        ## product description
        <Column ss:AutoFitWidth="1" ss:Width="239.25"  />
        ## Qty Ordered
        <Column ss:AutoFitWidth="1" ss:Width="54.75"  />
        ## UoM Ordered
        <Column ss:AutoFitWidth="1" ss:Width="54.75"  />
        ## Qty Delivered
        <Column ss:AutoFitWidth="1" ss:Width="68.25"  />
        ## UoM Delivered
        <Column ss:AutoFitWidth="1" ss:Width="68.25"  />
        ## Packing
        <Column ss:AutoFitWidth="1" ss:Width="60.25" />
        ## Qty to deliver
        <Column ss:AutoFitWidth="1" ss:Width="50.5" />
        ## Transport
        <Column ss:AutoFitWidth="1" ss:Width="55.00" />
        ## Transport file
        <Column ss:AutoFitWidth="1" ss:Width="55.75" />
        ## CDD
        <Column ss:AutoFitWidth="1" ss:Width="55.75" />
        ## ETA
        <Column ss:AutoFitWidth="1" ss:Width="50" />
        ## RTS Date
        <Column ss:AutoFitWidth="1" ss:Width="50" />

        <Row ss:Height="18">
            <Cell ss:StyleID="big_header"><Data ss:Type="String">FIELD ORDER FOLLOW-UP per CLIENT</Data><NamedCell ss:Name="Print_Area"/></Cell>
        </Row>

        <Row ss:Height="10"></Row>

        ## WORKSHEET HEADER
        <Row>
            <Cell ss:StyleID="file_header" ss:MergeAcross="1"><Data ss:Type="String">${_('Instance information')|x}</Data></Cell>
            <Cell ss:StyleID="ssCell"><Data ss:Type="String"></Data></Cell>
            <Cell ss:StyleID="file_header" ss:MergeAcross="4"><Data ss:Type="String">${_('Request parameters')|x}</Data></Cell>
        </Row>
        <Row>
            <Cell ss:StyleID="ssCell"><Data ss:Type="String">${_('Name:')|x}</Data></Cell>
            <Cell ss:StyleID="ssCellBlue"><Data ss:Type="String">${r.company_id.instance_id.instance or '-'|x}</Data></Cell>
            <Cell ss:StyleID="ssCell"><Data ss:Type="String"></Data></Cell>
            <Cell ss:StyleID="ssCell" ss:MergeAcross="1"><Data ss:Type="String">${_('Partner:')|x}</Data></Cell>
            <Cell ss:StyleID="ssCellBlue" ss:MergeAcross="2"><Data ss:Type="String">${r.partner_id and r.partner_id.name or '-'|x}</Data></Cell>
        </Row>
        <Row>
            <Cell ss:StyleID="ssCell"><Data ss:Type="String">${_('Address:')|x}</Data></Cell>
            <Cell ss:StyleID="ssCellBlue"><Data ss:Type="String">${r.company_id.partner_id.name or '-'|x}</Data></Cell>
            <Cell ss:StyleID="ssCell"><Data ss:Type="String"></Data></Cell>
            <Cell ss:StyleID="ssCell" ss:MergeAcross="1"><Data ss:Type="String">${_('Date start:')|x}</Data></Cell>
            % if r.start_date not in (False, 'False'):
            <Cell ss:StyleID="short_date" ss:MergeAcross="2"><Data ss:Type="DateTime">${r.start_date|n}T00:00:00.000</Data></Cell>
            % else:
            <Cell ss:StyleID="ssCell" ss:MergeAcross="2"><Data ss:Type="String"></Data></Cell>
            % endif
        </Row>
        <Row>
            <Cell ss:StyleID="ssCell"><Data ss:Type="String"></Data></Cell>
            <Cell ss:StyleID="ssCellBlue"><Data ss:Type="String">${r.company_id.partner_id.address[0].street or ''|x}</Data></Cell>
            <Cell ss:StyleID="ssCell"><Data ss:Type="String"></Data></Cell>
            <Cell ss:StyleID="ssCell" ss:MergeAcross="1"><Data ss:Type="String">${_('Date end:')|x}</Data></Cell>
            % if r.end_date not in (False, 'False'):
            <Cell ss:StyleID="short_date" ss:MergeAcross="2"><Data ss:Type="DateTime">${r.end_date|n}T00:00:00.000</Data></Cell>
            % else:
            <Cell ss:StyleID="ssCell" ss:MergeAcross="2"><Data ss:Type="String"></Data></Cell>
            % endif
        </Row>
        <Row>
            <Cell ss:StyleID="ssCell"><Data ss:Type="String"></Data></Cell>
            <Cell ss:StyleID="ssCellBlue"><Data ss:Type="String">${r.company_id.partner_id.address[0].zip|x} ${r.company_id.partner_id.address[0].city|x}</Data></Cell>
            <Cell ss:StyleID="ssCell"><Data ss:Type="String"></Data></Cell>
            <Cell ss:StyleID="ssCell" ss:MergeAcross="1"><Data ss:Type="String">${_('Date of the request:')|x}</Data></Cell>
            % if r.report_date not in (False, 'False'):
            <Cell ss:StyleID="short_date" ss:MergeAcross="2"><Data ss:Type="DateTime">${r.report_date[0:10]|n}T${r.report_date[11:19]|n}.000</Data></Cell>
            % else:
            <Cell ss:StyleID="ssCell" ss:MergeAcross="2"><Data ss:Type="String"></Data></Cell>
            % endif
        </Row>
        <Row>
            <Cell ss:StyleID="ssCell"><Data ss:Type="String"></Data></Cell>
            <Cell ss:StyleID="ssCellBlue"><Data ss:Type="String">${r.company_id.partner_id.address[0].country_id and r.company_id.partner_id.address[0].country_id.name or ''|x}</Data></Cell>
            <Cell ss:StyleID="ssCell"><Data ss:Type="String"></Data></Cell>
            <Cell ss:StyleID="ssCell" ss:MergeAcross="1"><Data ss:Type="String"></Data></Cell>
            <Cell ss:StyleID="ssCell" ss:MergeAcross="2"><Data ss:Type="String"></Data></Cell>
        </Row>

        <Row></Row>

        <%
            headers_list = [
                _('Order ref'),
                _('Customer ref'),
                _('PO ref'),
                _('Status'),
                _('Received'),
                _('RDD'),
                _('Item'),
                _('Code'),
                _('Description'),
                _('Qty ordered'),
                _('UoM ordered'),
                _('Qty delivered'),
                _('UoM delivered'),
                _('Packing'),
                _('Qty to deliver'),
                _('Transport'),
                _('Transport file'),
                _('CDD'),
                _('ETA'),
                _('RTS Date'),
            ]
        %>

        <Row>
        % for h in headers_list:
            <Cell ss:StyleID="line_header"><Data ss:Type="String">${h|x}</Data></Cell>
        % endfor
        </Row>

        % for o in getOrders(r):
            % for line in getLines(o, grouped=True):
            <Row ss:Height="11.25">
                <Cell ss:StyleID="line_left"><Data ss:Type="String">${o.name|x}</Data></Cell>
                <Cell ss:StyleID="line_left"><Data ss:Type="String">${o.client_order_ref or ''|x}</Data></Cell>
                <Cell ss:StyleID="line_left"><Data ss:Type="String">${line.get('po_name', '')|x}</Data></Cell>
                <Cell ss:StyleID="line_left"><Data ss:Type="String">${getSel(o, 'state')|x}</Data></Cell>
                <Cell ss:StyleID="line_left"><Data ss:Type="String">${saleUstr(formatLang(o.date_order, date=True))|x}</Data></Cell>
                <Cell ss:StyleID="line_left"><Data ss:Type="String">${o.delivery_requested_date and saleUstr(formatLang(o.delivery_requested_date, date=True)) or ''|x}</Data></Cell>
                <Cell ss:StyleID="line_center"><Data ss:Type="String">${line.get('line_number', '-')|x}</Data></Cell>
                <Cell ss:StyleID="line_left"><Data ss:Type="String">${line.get('product_code', '-') or ''|x}</Data></Cell>
                <Cell ss:StyleID="line_left"><Data ss:Type="String">${line.get('product_name', '-') or ''|x}</Data></Cell>
                % if line.get('ordered_qty'):
                <Cell ss:StyleID="line_right"><Data ss:Type="Number">${line.get('ordered_qty')}</Data></Cell>
                % else:
                <Cell ss:StyleID="line_left"><Data ss:Type="String">N/A</Data></Cell>
                % endif
                <Cell ss:StyleID="line_left"><Data ss:Type="String">${line.get('uom_id', '-')|x}</Data></Cell>
                % if line.get('delivered_qty'):
                <Cell ss:StyleID="line_right"><Data ss:Type="Number">${line.get('delivered_qty')}</Data></Cell>
                % else:
                <Cell ss:StyleID="line_left"><Data ss:Type="String">N/A</Data></Cell>
                % endif
                <Cell ss:StyleID="line_left"><Data ss:Type="String">${line.get('delivered_uom', '')|x}</Data></Cell>
                <Cell ss:StyleID="line_left"><Data ss:Type="String">${line.get('packing', '')|x}</Data></Cell>
                % if line.get('backordered_qty') and line.get('backordered_qty') >= 0:
                <Cell ss:StyleID="line_right"><Data ss:Type="Number">${line.get('backordered_qty')}</Data></Cell>
                % else:
                <Cell ss:StyleID="line_left"><Data ss:Type="String">0 (+${abs(line.get('backordered_qty', 0.00))|x})</Data></Cell>
                % endif
                % if o.transport_type and o.transport_type not in (False, 'False', ''):
                <Cell ss:StyleID="line_left"><Data ss:Type="String">${getSel(o, 'transport_type')|x}</Data></Cell>
                % else:
                <Cell ss:StyleID="line_left"><Data ss:Type="String"></Data></Cell>
                % endif
                <Cell ss:StyleID="line_left"><Data ss:Type="String">${line.get('shipment')|x}</Data></Cell>
                <Cell ss:StyleID="line_left"><Data ss:Type="String">${line.get('cdd', False) not in (False, 'False') and saleUstr(formatLang(line.get('cdd'), date=True)) or ''|x}</Data></Cell>
                <Cell ss:StyleID="line_left"><Data ss:Type="String">${line.get('eta', False) not in (False, 'False') and saleUstr(formatLang(line.get('eta'), date=True)) or ''|x}</Data></Cell>
                <Cell ss:StyleID="line_left"><Data ss:Type="String">${line.get('rts', False) not in (False, 'False') and saleUstr(formatLang(line.get('rts'), date=True)) or ''|x}</Data></Cell>
            </Row>
            % endfor

        % endfor

    </Table>

    <WorksheetOptions xmlns="urn:schemas-microsoft-com:office:excel">
        <PageSetup>
            <Layout x:Orientation="Landscape"/>
            <Footer x:Data="Page &amp;P of &amp;N"/>
        </PageSetup>
        <Selected/>
        <Panes>
            <Pane>
                <Number>3</Number>
                <ActiveRow>17</ActiveRow>
            </Pane>
        </Panes>
        <ProtectObjects>False</ProtectObjects>
        <ProtectScenarios>False</ProtectScenarios>
    </WorksheetOptions>
</ss:Worksheet>
% endfor
</Workbook>
