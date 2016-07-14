<?xml version="1.0"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
xmlns:o="urn:schemas-microsoft-com:office:office"
xmlns:x="urn:schemas-microsoft-com:office:excel"
xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"
xmlns:html="http://www.w3.org/TR/REC-html40">
<DocumentProperties xmlns="urn:schemas-microsoft-com:office:office">
<Title>${_('Register Lines')}</Title>
</DocumentProperties>
<Styles>
<Style ss:ID="ssH">
<Alignment ss:Horizontal="Center" ss:Vertical="Center" ss:WrapText="1"/>
<Font ss:Bold="1" />
<Borders>
  <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" />
  <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" />
  <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" />
  <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" />
</Borders>
</Style>
<Style ss:ID="ssBorder">
<Alignment ss:Vertical="Center" ss:WrapText="1"/>
<Borders>
  <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" />
  <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" />
  <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" />
  <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" />
</Borders>
</Style>
<Style ss:ID="ssBorderDate">
<Alignment ss:Vertical="Center" ss:WrapText="1"/>
<Borders>
  <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" />
  <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" />
  <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" />
  <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" />
</Borders>
<NumberFormat ss:Format="Short Date" />
</Style>
<Style ss:ID="ssNumber">
<Borders>
  <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" />
  <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" />
  <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" />
  <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" />
</Borders>
<Alignment ss:Horizontal="Right" ss:Vertical="Center" ss:WrapText="1"/>
<NumberFormat ss:Format="#,##0.00"/>
</Style>
</Styles>
<Worksheet ss:Name="Sheet">
<Table ss:ExpandedColumnCount="17" ss:ExpandedRowCount="${len(objects)+1}" x:FullColumns="1"
x:FullRows="1">
% for x in range(0,17):
<Column ss:AutoFitWidth="1" ss:Width="70" />
% endfor
<Row>
% for header in [_('Document Date'), _('Posting Date'), _('Sequence'), _('Description'), _('Reference'), _('Account'), _('Third Party'), _('Amount In'), _('Amount Out'), _('Currency'), _('Output In'), _('Output Out'), _('Output Currency'), _('State'), _('Register Name')]:
<Cell ss:StyleID="ssH"><Data ss:Type="String">${header}</Data></Cell>
% endfor
</Row>
% for o in objects:
<Row>
% if o.document_date and o.document_date != 'False':
<Cell ss:StyleID="ssBorderDate">
        <Data ss:Type="DateTime">${o.document_date|n}T00:00:00</Data>
</Cell>
% else:
<Cell ss:StyleID="ssBorder">
        <Data ss:Type="String"> </Data>
</Cell>
% endif
% if o.date and o.date != 'False':
<Cell ss:StyleID="ssBorderDate">
        <Data ss:Type="DateTime">${o.date|n}T00:00:00</Data>
</Cell>
% else:
<Cell ss:StyleID="ssBorder">
        <Data ss:Type="String"> </Data>
</Cell>
% endif
<Cell ss:StyleID="ssBorder">
        <Data ss:Type="String">${(o.sequence_for_reference or '')|x}</Data>
</Cell>
<Cell ss:StyleID="ssBorder">
        <Data ss:Type="String">${(o.name or '')|x}</Data>
</Cell>
<Cell ss:StyleID="ssBorder">
        <Data ss:Type="String">${(o.ref or '')|x}</Data>
</Cell>
<Cell ss:StyleID="ssBorder">
        <Data ss:Type="String">${o.account_id and o.account_id.code or ''} - ${(o.account_id and o.account_id.name or '')|x}</Data>
</Cell>
<Cell ss:StyleID="ssBorder">
        <Data ss:Type="String">${(o.partner_id and o.partner_id.name or o.employee_id and o.employee_id.name or o.transfer_journal_id and o.transfer_journal_id.code or '')|x}</Data>
</Cell>
<Cell ss:StyleID="ssNumber">
        <Data ss:Type="Number">${o.amount_in or '0.0'}</Data>
</Cell>
<Cell ss:StyleID="ssNumber">
        <Data ss:Type="Number">${o.amount_out or '0.0'}</Data>
</Cell>
<Cell ss:StyleID="ssBorder">
        <Data ss:Type="String">${(o.currency_id and o.currency_id.name or '')|x}</Data>
</Cell>
<Cell ss:StyleID="ssNumber">
        <Data ss:Type="Number">${o.output_amount_debit or '0.0'}</Data>
</Cell>
<Cell ss:StyleID="ssNumber">
        <Data ss:Type="Number">${o.output_amount_credit or '0.0'}</Data>
</Cell>
<Cell ss:StyleID="ssBorder">
        <Data ss:Type="String">${(o.output_currency and o.output_currency.name or '')|x}</Data>
</Cell>
<Cell ss:StyleID="ssBorder">
        <Data ss:Type="String">${getSel(o, 'state')|x}</Data>
</Cell>
<Cell ss:StyleID="ssBorder">
        <Data ss:Type="String">${o.statement_id and o.statement_id.name or ''}</Data>
</Cell>
</Row>
% endfor
</Table>
<AutoFilter x:Range="R1C1:R1C17" xmlns="urn:schemas-microsoft-com:office:excel">
</AutoFilter>
<WorksheetOptions xmlns="urn:schemas-microsoft-com:office:excel">
   <FitToPage/>
   <PageSetup>
    <Layout x:Orientation="Landscape"/>
    <Footer x:Data="Page &amp;P of &amp;N"/>
   </PageSetup>
</WorksheetOptions>
</Worksheet>
</Workbook>
