% if editable:
    <input
        type="hidden" 
        kind="${kind}" 
        name="${name}" 
        id="${name}" 
        value="${value}"
        ${py.attrs(attrs)}>
    <input
        type="checkbox" 
        kind="${kind}" 
        class="checkbox"
        id="${name}_checkbox_" 
        ${py.checker(value)}
        ${py.attrs(attrs)}>
    % if error:
        <span class="fielderror">${error}</span>
    % endif
% else:
    % if value == '?':
    <span kind="${kind}" class="text_null_boolean" name="${name}" id="${name}" >${value}</span>
    % else:
    <input
        type="checkbox"
        kind="${kind}"
        class="checkbox" 
        id="${name}" 
        value="${value}"
        disabled="disabled"
        ${py.checker(value)}>
   % endif
% endif

