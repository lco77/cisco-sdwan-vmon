// Define CRUD objects needed
const definitionDefault =           'template_policy_vsmart_definition_by_policyId';
const definitionMap = {
    'control':                      'template_policy_definition_control',
    'appRoute':                     'template_policy_definition_approute',
    'vedgeRoute':                   'template_policy_definition_vedgeroute',
    'data':                         'template_policy_definition_data',
    'cflowd':                       'template_policy_definition_cflowd',
    'zoneBasedFW':                  'template_policy_definition_zonebasedfw',
};
const listMap = {
    'app':                          'template_policy_list_app',
    'color':                        'template_policy_list_color',
    'community':                    'template_policy_list_community',
    'expandedcommunity':            'template_policy_list_expandedcommunity',
    'dataprefixall':                'template_policy_list_dataprefixall',
    'policer':                      'template_policy_list_policer',
    'ipprefixall':                  'template_policy_list_ipprefixall',
    'site':                         'template_policy_list_site',
    'appprobe':                     'template_policy_list_appprobe',
    'class':                        'template_policy_list_class',
    'sla':                          'template_policy_list_sla',
    'tloc':                         'template_policy_list_tloc',
    'vpn':                          'template_policy_list_vpn',
    'aspath':                       'template_policy_list_aspath',
    'dataprefix':                   'template_policy_list_dataprefix',
    'prefix':                       'template_policy_list_prefix',
};

// Render tabs layout
function makeListTabs(divHeader,divContent,callback) {
    const divHead = (list,title) => `
        <!-- ${list} -->
        <button class="list nav-link text-start" id="nav-${list}-tab" data-bs-toggle="tab"
            data-bs-target="#nav-${list}" type="button" role="tab" aria-controls="nav-${list}" aria-selected="false"
            data-object="${list}">${title}
        </button>`;
    const divCont = (list) => `
    <!-- ${list} -->
    <div class="tab-pane fade" id="nav-${list}" role="tabpanel" aria-labelledby="nav-${list}-tab">
        <div class="row">
            <div id="div-${list}" class="col-lg-12">
                <table id="table-${list}" class="table table-striped table-secondary" width="100%"></table>
            </div>
        </div>
    </div>`;
    var head = '';
    var content = '';
    Object.keys(listMap).forEach(k=>{
        head    = head + divHead(listMap[k],k);
        content = content + divCont(listMap[k],k);
    });
    $('#'+divHeader).html(head);
    $('#'+divContent).html(content);
    callback();
};

// Render list index tables
function makeListTable(object, data) {
    // Add action column 
    data.header.columns.push({
        'title': 'Actions',
        'property': 'action',
        'visible': true
    });
    // Clear existing DataTable if any
    if (DataTable.isDataTable('#table-' + object)) {
        var table = $('#table-' + object).DataTable();
        table.destroy(remove = true);
        $('#div-' + object).html(`<table id="table-${object}" class="table table-striped table-secondary" width="100%"></table>`);
    };
    // Init DataTable
    $('#table-' + object).show();
    $('#table-' + object).DataTable({
        data: data.data,
        columns: data.header.columns.map(e => { return { 'data': e.property, 'title': e.title, 'visible': true } })
                                    .filter(e=> { if (e.data != 'type') {return e;} }),
        columnDefs: [{
            targets: '_all',
            defaultContent: '-',
        }, {
            // Entries column
            targets: 1,
            render: function (data, type, row, meta) {
                let o = '';
                const key = (k) => `<span class="pull-left">${k}:</span>`;
                const val = (v) => `<span class="text-success pull-right">${v}</span>`;
                const obj = (o) => `<ul class="">${o}</ul>`;
                row.entries.forEach(e => {
                    o = o + '<li>';
                    Object.keys(e).forEach(k => {
                        let v = e[k];
                        o = o + '' + key(k) + '&nbsp;' + val(v) + '&nbsp;';
                    })
                    o = o + '</li>';
                });
                return obj(o);
            }
        }, {
            // References column
            targets: 2,
            render: function (data, type, row, meta) {
                let o = '';
                const obj = (o) => `<ul class="">${o}</ul>`;
                const btnShow = (type,uuid,count) => `<a class="show fw-bold badge bg-info" data-type="${type}" data-id="${uuid}" href="#">${count}</a>`;
                if (row.referenceCount > 0 ) {
                    o = btnShow(listMap[row.type.toLowerCase()],row.listId,row.referenceCount);
                } else {
                    o = '0';
                }
                return obj(o);
            }
        },{
            // Last updated column
            targets: 4,
            render: function (data, type, row, meta) {
                let colName = meta.settings.aoColumns[meta.col].data;
                if (colName == 'lastUpdated' || colName == 'lastupdated' || colName == 'time-date' || colName == 'uptime-date') {
                    return toISOStringUTC(data);
                } else { return data }
            }
        },{ // Action buttons column
            targets: 5,
            render: function (data, type, row, meta) {
              const btnEdit   = (uuid) => `<button class="edit btn btn-success"  data-id="${uuid}">Edit</button>`;
              const btnDelete = (uuid) => `<button class="delete btn btn-warning" data-id="${uuid}">Delete</button>`;
              const btnGrp = (btnA, btnB) => `<p class="bs-component">${btnA} ${btnB}</p>`;
              let btnA='';
              if (! row.readOnly) {
                  btnA = btnEdit(row.listId);
              }
              let btnB = '';
              if (row.referenceCount == 0 ) {
                btnB = btnDelete(row.listId);
              }
              if (btnA+btnA != '') {
                  return btnGrp(btnA, btnB);
              } else {
                  return;
              }

            }
          }],
        "pageLength": 200
    });
    // Register show buttons
    $("a.show").click(function (e) {
        //console.log('click');
        let type = $(this).attr('data-type');
        let uuid = $(this).attr('data-id');
        showListReferences(type,uuid,'editModal');
    });
};

// Show modal & load data
function showListReferences(object,uuid,container) {
    // Display modal
    const spinner = `
        <li id="modal-loader" class="nav-item spinner-border text-warning" role="status" style="display: none;">
        <span class="visually-hidden">Loading...</span>
        </li>`;
    const modal = new bootstrap.Modal(document.getElementById(container));
    $('#'+container+'-title').html('');
    $('#'+container+'-body').html(spinner);
    $('#'+container+'-footer').html('');
    modal.show();
    $('#modal-loader').show();
    // // Get list info
    crud('read',object,{'id':uuid}).then(data=>{
        $('#'+container+'-title').html(data.name);
        // Get refs data asynchronously
        getListReferences(data.references).then(refs=>{
            console.log(refs);
            // Show modal
            renderReferences(refs,container+'-body');
        });        
    })
};

// Fetch refs data
async function getListReferences (array) {
    // Prepare crud requests
    const responses = await Promise.all(array.map(async e => {
        if (e.type in definitionMap) {
            const data = await crud('read',definitionMap[e.type], {'id':e.id} );
            return data;
        } else {
            // default to vsmart policy definition
            const data = await crud('read',definitionDefault, {'id':e.id} );
            return data;
        }
      }));    
    return responses;
};

// Render refs content
//   name | type | data
function  renderReferences(refs,container) {
    // Clear existing DataTable if any
    if (DataTable.isDataTable('#table-refs')) {
        var table = $('#table-refs').DataTable();
        table.destroy(remove = true);
    };
    // Init DataTable
    $('#' + container).html(`<table id="table-refs" class="table table-striped table-secondary" width="100%"></table>`);
    $('#table-refs').show();
    $('#table-refs').DataTable({
        data: refs,
        columns: [
            { 'data': 'name', 'title': 'Name', 'visible': true },
            { 'data': 'type', 'title': 'Type', 'visible': true },
            { 'data': 'data', 'title': 'Details', 'visible': true },
        ],
        columnDefs: [{
            targets: '_all',
            defaultContent: '-',
        }, {
            // Name column
            targets: 0,
            render: function (data, type, row, meta) {
                if ('name' in row) {
                    return `<span class="text-success">${row.name}</span>`;
                } else {
                    return `<span class="text-success">${row.policyName}</span>`;
                }
            }
        }, {
            // Type column
            targets: 1,
            render: function (data, type, row, meta) {
                if ('type' in row) {
                    return row.type;
                } else {
                    return row.policyType;
                }
            }
        },{
            // Data column
            targets: 2,
            render: function (data, type, row, meta) {
                // Generic renderer by default
                return renderRawReference(row,meta);
            }
        }],
        "pageLength": 200
    });
};

// Generic renderer for all object types
function renderRawReference(ref,meta) {
    const t  = (content) => `<table>${content}</table>`;
    const tr = (content) => `<tr>${content}</tr>`;
    const td = (content) => `<td>${content}</td>`;
    const show = (id) => `<button class="btn btn-sm btn-outline-info" onclick="hljs.highlightAll();$('#pre-${id}').toggle()">Show</button>`;
    const code = (id,content) => `<pre id="pre-${id}" style="display:none;"><code class="language-json hljs">${content}</code></pre>`;
    const span = (content) => `<span class="text-info">${content}</span>`;
    var i = 0;
    return t(Object.keys(ref)
                 .map(e=>{
                    if (typeof ref[e] == 'object') {
                        i = i + 1;
                        let id = meta.row + '-' + i;
                        let btn = show(id);
                        let val = code( id, JSON.stringify( ref[e],null,1 ) );
                        return tr(td(e)+td(btn+val));
                    } else {
                        let val = span(ref[e]);
                        return tr(td(e)+td(val));
                    }
                 })
                 .join('')
    );
};