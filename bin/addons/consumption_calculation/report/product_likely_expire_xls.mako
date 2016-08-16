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
    </Style>
    <Style ss:ID="line">
        <Alignment ss:Horizontal="Center" ss:Vertical="Center" ss:WrapText="1"/>
        <Borders>
          <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" />
          <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" />
          <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" />
          <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" />
        </Borders>
    </Style>
    <Style ss:ID="line_number">
        <Alignment ss:Horizontal="Right" ss:Vertical="Top" ss:WrapText="1"/>
        <Borders>
            <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" />
            <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" />
            <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" />
            <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" />
        </Borders>
        <NumberFormat ss:Format="#,##0.00"/>
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
    </Style>
</Styles>
<ss:Worksheet ss:Name="Products likely to expire">
% for o in objects:
<Table x:FullColumns="1" x:FullRows="1">
<%
dates = getReportDates(o)
n_columns = 6 + len(dates)
n_header_columns = 3
n_header_colspan = n_columns - 3
if n_header_colspan < 0:
    n_header_colspan = 1
%>
<Column ss:AutoFitWidth="1" ss:Width="120" />
<Column ss:AutoFitWidth="1" ss:Width="250" />
<Column ss:AutoFitWidth="1" ss:Width="80" />
% for d, d_str in dates:
<Column ss:AutoFitWidth="1" ss:Width="80" />
% endfor
<Column ss:AutoFitWidth="1" ss:Width="80" />
<Column ss:AutoFitWidth="1" ss:Width="80" />
## criteria header
<Row>
<Cell ss:StyleID="header"><Data ss:Type="String">Location</Data></Cell>
<Cell ss:StyleID="header"><Data ss:Type="String">Period</Data></Cell>
<Cell ss:StyleID="header" ss:MergeAcross="2"><Data ss:Type="String">Consumption</Data></Cell>
<%
cols = n_header_colspan - 2
if cols < 0:
    cols = 0
%>
% for n in range(cols):
<Cell ss:StyleID="line"><Data ss:Type="String"></Data></Cell>
% endfor
</Row>
<Row>
<Cell ss:StyleID="line" ><Data ss:Type="String">${(o.msf_instance or '')|x}</Data></Cell>
<Cell ss:StyleID="line" ><Data ss:Type="String">${(getReportPeriod(o) or '')|x}</Data></Cell>
<Cell ss:StyleID="line" ss:MergeAcross="2"><Data ss:Type="String">${(getReportConsumptionType(o) or '')|x}</Data></Cell>
% for n in range(cols):
<Cell ss:StyleID="line"><Data ss:Type="String"></Data></Cell>
% endfor
</Row>
<Row>
% for n in range(n_columns):
<Cell ss:StyleID="line" ><Data ss:Type="String"></Data></Cell>
% endfor
</Row>
## products to expire header
<Row>
<Cell ss:StyleID="header"><Data ss:Type="String">Product Code</Data></Cell>
<Cell ss:StyleID="header"><Data ss:Type="String">Product Description</Data></Cell>
<Cell ss:StyleID="header"><Data ss:Type="String">Monthly Consumption</Data></Cell>
% for d, d_str in dates:
<Cell ss:StyleID="header"><Data ss:Type="String">${d_str|x}</Data></Cell>
% endfor
<Cell ss:StyleID="header"><Data ss:Type="String">In Stock</Data></Cell>
<Cell ss:StyleID="header"><Data ss:Type="String">Total Expired</Data></Cell>
<Cell ss:StyleID="header"><Data ss:Type="String">Total Value</Data></Cell>
</Row>
## lines
% for line in o.line_ids:
<Row>
<Cell ss:StyleID="line"><Data ss:Type="String">${(line.product_id.default_code or '')|x}</Data></Cell>
<Cell ss:StyleID="line"><Data ss:Type="String">${(line.product_id.name or '')|x}</Data></Cell>
<Cell ss:StyleID="line_number"><Data ss:Type="Number">${line.consumption or 0.}</Data></Cell>
% for i in getLineItems(line):
    ## line items
    % if i.expired_qty:
    <Cell ss:StyleID="line"><Data ss:Type="String">${formatLang(i.available_qty) or 0.00} (${(formatLang(i.expired_qty) or 0.00)})</Data></Cell>
    % endif
    % if not i.expired_qty:
    <Cell ss:StyleID="line"><Data ss:Type="Number">${formatLang(i.available_qty) or 0.00}</Data></Cell>
    % endif
% endfor
<Cell ss:StyleID="line_number"><Data ss:Type="Number">${line.in_stock or 0.}</Data></Cell>
<Cell ss:StyleID="line_number"><Data ss:Type="Number">${line.total_expired or 0.}</Data></Cell>
<Cell ss:StyleID="line_number"><Data ss:Type="Number">${line.total_value or 0.}</Data></Cell>
</Row>
% endfor
## total row
<Row>
<Cell ss:StyleID="line"><Data ss:Type="String"></Data></Cell>
<Cell ss:StyleID="line"><Data ss:Type="String"></Data></Cell>
<Cell ss:StyleID="line"><Data ss:Type="String"></Data></Cell>
% for i in getLineItems(line):
    ## line items
    <Cell ss:StyleID="line"><Data ss:Type="String"></Data></Cell>
% endfor
<Cell ss:StyleID="line"><Data ss:Type="String"></Data></Cell>
<Cell ss:StyleID="line"><Data ss:Type="String"></Data></Cell>
<Cell ss:StyleID="line_number"><Data ss:Type="Number">${getExpiryValueTotal(o) or 0.}</Data></Cell>
</Row>
</Table>
% endfor
<x:WorksheetOptions/>
</ss:Worksheet>
% for d, d_str in dates:
<%
worksheet_name = d_str.replace('/', '-')
%>
<ss:Worksheet ss:Name="${worksheet_name}">
<Table x:FullColumns="1" x:FullRows="1">
<Column ss:AutoFitWidth="1" ss:Width="120" />
<Column ss:AutoFitWidth="1" ss:Width="250" />
<Column ss:AutoFitWidth="1" ss:Width="80" />
<Column ss:AutoFitWidth="1" ss:Width="80" />
<Column ss:AutoFitWidth="1" ss:Width="80" />
<Column ss:AutoFitWidth="1" ss:Width="80" />
<Column ss:AutoFitWidth="1" ss:Width="80" />
<Row>
<Cell ss:StyleID="header" ><Data ss:Type="String">Product Code</Data></Cell>
<Cell ss:StyleID="header" ><Data ss:Type="String">Product Description</Data></Cell>
<Cell ss:StyleID="header" ><Data ss:Type="String">Batch Number</Data></Cell>
<Cell ss:StyleID="header" ><Data ss:Type="String">Expiry Date</Data></Cell>
<Cell ss:StyleID="header" ><Data ss:Type="String">Location</Data></Cell>
<Cell ss:StyleID="header" ><Data ss:Type="String">Available Qty</Data></Cell>
<Cell ss:StyleID="header" ><Data ss:Type="String">Expiry Qty</Data></Cell>
</Row>
% for il in getMonthItemLines(o, d):
<Row>
<Cell ss:StyleID="line" ><Data ss:Type="String">${il.item_id.line_id.product_id.default_code or ''|x}</Data></Cell>
<Cell ss:StyleID="line" ><Data ss:Type="String">${il.item_id.line_id.product_id.name or ''|x}</Data></Cell>
<Cell ss:StyleID="line" ><Data ss:Type="String">${il.lot_id.name}</Data></Cell>
<Cell ss:StyleID="line" ><Data ss:Type="String">${(formatLang(il.expired_date, date=True) or '')}</Data></Cell>
<Cell ss:StyleID="line" ><Data ss:Type="String">${il.location_id.name}</Data></Cell>
<Cell ss:StyleID="line_number" ><Data ss:Type="Number">${il.available_qty or 0.}</Data></Cell>
<Cell ss:StyleID="line_number" ><Data ss:Type="Number">${il.expired_qty or 0.}</Data></Cell>
</Row>
% endfor
</Table>
<x:WorksheetOptions/>
</ss:Worksheet>
% endfor
</Workbook>
