
// Fetches device templates values & display result into DOM element
function showTemplateValues(url, templateId, divTemplateValues) {
    //console.log('click showTemplateValues');
    $('#loader').show();
    getURL(url).then(result=>{
        //console.log(result);
        $('#loader').hide();
        if (result.data) {
            table = makeInputFormMulti(result,templateId);
            $('#'+divTemplateValues).html(table);
        } else {
            $('#'+divTemplateValues).html(makeAlert('danger','Oops!','Failed to get data; please retry later...'));
        }
        
    });
    
};

// Download device templates values as CSV file
function downloadInputFormMulti(templateId) {
    data = readInputFormMulti(templateId);
    array = [];
    Object.keys(data).forEach(function(e){array.push(data[e])})
    //console.log(array);
    let csv = '';
    let dataLine= [];
    // Make header
    let head = array[0];
    Object.keys(head).map(key => {
      csv = csv + '"' + key       + '",';
    });
    csv = csv.slice(0, -1);
    csv = csv + '\n';
    // Make data
    array.forEach(function(d){
        dataLine = '';
        Object.keys(array[0]).map(key => {
            dataLine = dataLine + '"' + d[key] + '",';
        });
        dataLine = dataLine.slice(0, -1);
        dataLine = dataLine + '\n';
        csv = csv + dataLine;
    })
    var hiddenElement = document.createElement('a');
    hiddenElement.href = 'data:text/csv;charset=utf-8,' + encodeURI(csv);
    hiddenElement.target = '_blank';
    hiddenElement.download = 'data.csv';
    hiddenElement.click();
}

// Read device templates values form data
function readInputFormMulti(templateId) {
    let formId = 'form-' + templateId;
    let deviceSelector = `#${formId}  .device`;
    let dataSelector = `#${formId}  .form-control`;
    let data = {};
    // Init devices
    $(deviceSelector).each(function(e){
        let uuid = $(this).attr('data-id');
        data[uuid] = {};
        data[uuid]['csv-templateId'] = templateId;

    });
    // Fill device data
    $(dataSelector).each(function(e){
        let uuid = $(this).attr('data-uuid');
        let property = $(this).attr('data-property');
        let val = $(this).val();
        if (val == '') { val = 'TEMPLATE_IGNORE'};
        data[uuid][property] = val;
    });
    // Dump into array
    result = Object.keys(data).map(e=>{
        return data[e];
    });
    return result;
}

// Generate device templates values form
function makeInputFormMulti(input,templateId) {
    let header   = input.header;
    let data     = input.data;
    let formId   = 'form-' + templateId;
    const form   = (id,templateId,content) => `<form id="${id}" data-template-id="${templateId}" method="POST">${content}</form>`;
    const table  = (tableHead,tableContent) => `<table class="table table-striped table-secondary">${tableHead}${tableContent}</table>`;
    const cell   = (content,style) => `<td><span class="list-inline-item ${style}">${content}</span></td>`;
    const thead  = (id,content) => `<th data-id="${id}" class="device" style="min-width:200px; position:sticky; top:0">${content}</th>`;
    const item   = (content) => `<td>${content}</td>`;
    const option = (o) => {if (o){return cell('Optional','text-warning')} else {return cell('Required','text-danger')} };
    header = header.sort((a,b) => (a.breadcrumb > b.breadcrumb) ? 1 : ((b.breadcrumb > a.breadcrumb) ? -1 : 0));
    var tableHead = '<tr><th>Template</th><th>Variable</th><th>Type</th>'
        + data.map(d=>thead(d['csv-deviceId'],d['csv-host-name'])).join(' ')
        + '<th></th></tr>';
    var tableContent = header.map(h=>{ 
        let dataCells = data.map( d=> item(makeInputElement(h,d)) ).join(' ');
        return '<tr>'
            + cell(h.templateType,'text-info')
            + cell(h.variable,' ') 
            + cell(h.dataType,'text-success')
            + dataCells
            + option(h.optional)
            + '</tr>';
    }).join('');
    return form(formId,templateId,table(tableHead,tableContent));
}

// Generate input field for a specific device template value
function makeInputElement(head,data) {
    let ip    = data['csv-deviceIP'];
    let uuid    = data['csv-deviceId'];
    let value = data[head.property];
    let id = head.variable + '-' + ip;
    let prop = head.property;
    let name = head.variable + '-' + ip;
    let filter = `id="${id}" name="${name}" data-property="${prop}" data-uuid="${uuid}"`;
    const disabled = () => {
        if ( head['editable'] ) {
            return '';
        } else {
            //return 'disabled readonly';
            return 'readonly';
        }
    };
    const inputField = (value) => {
        let field = '';
        // Replace TEMPLATE_IGNORE value
        if (value == 'TEMPLATE_IGNORE') { value = '' };
        
        switch ( head['dataType'] ) {
            // enum
            case 'enum':
                const optionList = () => {
                    let list = '';
                    let select = head['values'];
                    //let select = [];
                    if ( head['optional'] ) {
                      select.push({'key':'','value':''});
                    }
                    select.forEach(function(element) {
                    if (element['key'] == value) {
                        list = list + `<option value="${element['key']}" selected>${element['value']}</option>`;
                    } else {
                        list = list + `<option value="${element['key']}">${element['value']}</option>`;
                    };
                    });
                    return list;
                };
                field = `<select ${filter} class="form-select form-select-sm form-control form-control-sm">
                            ${optionList()}
                            </select>`;
                break;  
            // boolean                  
            case 'boolean':
                const booleanList = (value) => {
                    let list = '';
                    switch ( value ) {
                        case 'true':
                            list = `<option value=""></option><option value="true" selected>True</option><option value="false">False</option>`;
                            break;
                        case 'false':
                            list = `<option value=""></option><option value="true">True</option><option value="false" selected>False</option>`;
                            break;
                        default:
                            list = `<option value="" selected></option><option value="true">True</option><option value="false">False</option>`;
                            break;
                    }
                    return list;
                }
                field = `<select ${filter} class="form-select form-select-sm form-control form-control-sm">
                            ${booleanList(value)}
                            </select>`;
                break;
            // others
            default:
                field = `<input type="text" ${filter} class="form-control form-control-sm" value="${value}" ${disabled()}>`;
                break; 
        };
        return field;
    };
    return inputField(value);
}

// Attach device template to one or more devices
function attachDeviceTemplate(templateId, data, redirect) {
    // Prepare payload (can contain data for multiple devices)
    let payload = {"deviceTemplateList": [{"templateId": templateId,"device": data,"isEdited": false,"isMasterEdited": false}]};
    console.log(payload);
    crud('create','template_device_config_attachfeature',{'data':payload}).then(data=>{
        if (data.id) {
            window.location.replace(redirect);
        } else {
            console.log(data.error);
        }
    });
  };