///////////////////////////////////////////////////////////////////
//                          API UTILS                            //
///////////////////////////////////////////////////////////////////

// Load CSRF Token
function getToken() {
  return $('meta[name=csrf-token]').attr('content');
}

// crud - Single async function to consume the CRUD api
// (see /api for supported objects and actions)
// crud( 'index',  'object', {          'arg1':val1, ...                 } ).then( data=>... );
// crud( 'create', 'object', {          'arg1':val1, ..., 'data':payload } ).then( data=>... );
// crud( 'read',   'object', { 'id':id, 'arg1':val1, ...                 } ).then( data=>... );
// crud( 'edit',   'object', { 'id':id, 'arg1':val1, ..., 'data':payload } ).then( data=>... );
// crud( 'delete', 'object', { 'id':id, 'arg1':val1, ..., 'data':payload } ).then( data=>... );
async function crud(action,object,params) {
  //console.log(params.data);
  const token    = getToken();
  const api = '/api';
  // map crud action to http method
  const map_crud = (action) =>{
    let actions = {'index':'get','read':'get','create':'post','edit':'post','delete':'delete'};
    return actions[action];
  };
  // url
  const url = (object,params) => {
    // resource path
    let url   = `${api}/${object}/${action}`;
    // query params
    let query = false;
    if (params) {
      query = Object.keys(params)
          .filter(e=>e!='data')
          .map(e=>{return `${e}=${params[e]}`})
          .join('&');
    };
    if (query) {url = `${url}?${query}`};
    return url;
  };
  // options
  const options = (params) => {
    let options = {};
    options.method  = map_crud(action);
    options.headers = {'Content-Type':'application/json','X-CSRFToken':token};
    if (params && params.hasOwnProperty('data')) { options.body = JSON.stringify(params.data); };
    return options;
  };
  // send request
  try {
    //console.log(options(params));
    const response = await fetch(url(object,params),options(params));
    //if (response.status === 200) { let data = await response.json(); };
    let data = await response.json();
    return data;
  } catch (error) {
    return {'error':true,'message':error};
  }
};

// Helper for Async / parallel CRUD requests
// objects = [{'action':a,'object':o,'params':p},...]
// returns the same objects with new data key for result
async function cruds(objects) {
  const responses = await Promise.all(objects.map(async e => {
    const data = await crud(e.action,e.object,e.params);
    e.data = data;
    return e;
  }));
  return responses;
}

// Async getURL for vMon API endpoints
async function getURL(url) {
  const token = getToken();
  const options = {'method':'get','Content-Type':'application/json;charset=utf-8','X-CSRFToken':token};
  try {
    const response = await fetch(url,options);
    if (!response.ok) {
      console.log(response.status);
      return {'error':response.status}
    }
    const data = await response.json();
    return data;
  } catch (error) {
    return {'error':true,'message':error};
  }
};


// Jobs
function showJobs(url,divHeader,divContent) {
  // valid registries
  const registries = {
    'started':    'Started',
    'deferred':   'Deferred',
    'finished':   'Finished',
    'failed':     'Failed',
    'scheduled':  'Scheduled',
  };
  // DOM templates
  const divHead = (list,title,active,aria_selected) => `
      <!-- ${list} -->
      <button class="list nav-link text-start ${active}" id="nav-${list}-tab" data-bs-toggle="tab"
          data-bs-target="#nav-${list}" type="button" role="tab" aria-controls="nav-${list}" aria-selected="${aria_selected}"
          data-object="${list}">${title}
      </button>`;
  const divCont = (list,active_show) => `
  <!-- ${list} -->
  <div class="tab-pane fade ${active_show}" id="nav-${list}" role="tabpanel" aria-labelledby="nav-${list}-tab">
      <div class="row">
          <div id="div-${list}" class="col-lg-12">
              <table id="table-${list}" class="table table-striped table-secondary" width="100%"></table>
          </div>
      </div>
  </div>`;
  // Init tabs
  let head = '';
  let content = '';
  let active = 'active';
  let active_show = 'active show';
  let aria_selected = 'true';
  Object.keys(registries).forEach(k=>{
      head    = head + divHead(k,registries[k],active,aria_selected);
      active = '';
      aria_selected = 'false';
      content = content + divCont(k,active_show);
      active_show = '';
  });
  $('#'+divHeader).html(head);
  $('#'+divContent).html(content);
  // get data
  getURL(url).then(data=>{
    console.log(data);
  });
};
///////////////////////////////////////////////////////////////////
//                         DOM  UTILS                            //
///////////////////////////////////////////////////////////////////

// makeNode - quickly construct a DOM node
// ex: myDiv=makeNode('div',{'class':'row'},'content');
function makeNode(name,options,text) {
  var node=document.createElement(name);
  for (var o in options) {
    node.setAttribute(o,options[o]);
  }
  if (text) {
    node.innerHTML=text;
  }
  return node;
}

function makeAlert(color,title,content,dismiss) {
  let btn = '';
  if (dismiss) {btn='<button type="button" class="btn-close" data-bs-dismiss="alert"></button>'};
  const alert = (color,title,content) => `
    <div class="alert alert-dismissible alert-${color}">
      ${btn}
      <h4 class="alert-heading">${title}</h4>
      ${content}
    </div>
  `;
  return alert(color,title,content);
}

///////////////////////////////////////////////////////////////////
//                         DATA UTILS                            //
///////////////////////////////////////////////////////////////////

// render JSON
function renderJSON(object,container) {
  let json = JSON.stringify(object, null, 1);
  $('#'+container).text(json);
  hljs.highlightAll();
}

// recursively delete key k from object o
function deleteKey(o,k) {
  if (Array.isArray(o)) {
    o.map(e=>{return deleteKey(e,k)});
  } else {
    Object.keys(o).forEach(key=>{
      if (key == k) { 
        delete o[k];
      } else if (typeof o[key] == 'object') {
        o[key] = deleteKey(o[key],k);
      }
    });
  };
  return o;
};

// recursively rename key k to j from object o
function replaceKey(o,k,j) {
  if (Array.isArray(o)) {
    o.map(e=>{return replaceKey(e,k,j)});
  } else {
    Object.keys(o).forEach(key=>{
      if (key == k) {
        let tmp = o[k];
        delete o[k];
        o[j] = tmp;
      } else if (typeof o[key] == 'object') {
        o[key] = replaceKey(o[key],k,j);
      }
    });
  };
  return o;
};

// toISOStringUTC - convert date into Cisco's supported format
function toISOStringUTC(data) {
  let date = new Date(data);
  return date.toISOString().substring(0, date.toISOString().length - 5)+' UTC';
}

function getFormData(id) {
  //console.log('form-id='+id);
  let myForm = document.getElementById(id);
  let formData = new FormData(myForm);
  let data = {};
  for (var [key, value] of formData.entries()) { 
    data[key] = value;
  }
  //console.log(data);
  return data;
}

function downloadFormData(id) {
  //console.log('form-id='+id);
  data = getFormData(id);
  let headLine = '';
  let dataLine= '';
  Object.keys(data).map(key => {
    headLine = headLine + '"' + key       + '",';
    dataLine = dataLine + '"' + data[key] + '",'}
  );
  // remove trailing comma
  headLine = headLine.slice(0, -1);
  dataLine = dataLine.slice(0, -1);
  // add cariage return
  headLine = headLine + '\n';
  dataLine = dataLine + '\n';
  let csv = headLine + dataLine;
  var hiddenElement = document.createElement('a');
  hiddenElement.href = 'data:text/csv;charset=utf-8,' + encodeURI(csv);
  hiddenElement.target = '_blank';
  hiddenElement.download = 'data.csv';
  hiddenElement.click();
}

function downloadDOMContent(selector) {
  data = $(selector).text();
  var hiddenElement = document.createElement('a');
  hiddenElement.href = 'data:text/txt;charset=utf-8,' + encodeURI(data);
  hiddenElement.target = '_blank';
  hiddenElement.download = 'data.txt';
  hiddenElement.click();
}
///////////////////////////////////////////////////////////////////
//                         ALARM UTILS                           //
///////////////////////////////////////////////////////////////////

// showAlarmCount - get alarm count, update DOM, refresh at interval
function showAlarmCount(contextElement, countElement, refreshInterval) {
  var getAlarmCount = function () {
    if ($(contextElement).attr('data-id') > 0) {
      crud('index','alarms_count').then(data=>{
        if (data.data && data.data[0] && data.data[0].count > 0) {
          $(countElement).addClass('text-danger');
        } else {
          $(countElement).removeClass('text-danger');
        }
      });
    }
  }
  getAlarmCount();
  setInterval(getAlarmCount, refreshInterval); 
};

// showAlarmDetails
function showAlarmDetails(id,modal,content,spinner) {
  $('#' + spinner).show();
  crud('read','alarms_uuid_by_alarm_uuid',{'alarm_uuid':id}).then(data=>{
      $('#' + spinner).hide();
      $('#'+content).text(JSON.stringify(data.data[0], null, 2));
      modal.show();
  });
};

// clearAlarm
function clearAlarm(id, buttonid, spinner) {
  $('#' + spinner).show();
  alarms = [];
  alarms.push(id);
  payload = {};
  payload['uuid'] = alarms;
  //console.log(payload);
  crud('create','alarms_markviewed',{'type':'active','data':payload}).then(data=>{
    $('#' + spinner).hide();
    if (data.data) {
      $('#' + buttonid).hide();
    }
  });
};

// showAlarms - fetch and display alarms
function showAlarms(alarmType, tableContainer, spinner) {
  $('#' + spinner).show();
  // Get alarms
  crud('index','alarms_notviewed',{'state':alarmType}).then(result=>{
    $('#' + spinner).hide();
    if (result.error) {
      $('#' + tableContainer).replaceWith(`
                <div class="alert alert-primary">
                  <h4 class="alert-heading text-center">Missing Context</h4>
                  <p class="mb-0 text-center">Select a context from the top menu</p>
                </div>`);
      return;
    }
    // Add action column 
    result.header.columns.push({
      'title': 'Actions',
      'property': 'action',
      'visible': true
    });
    // Clear existing DataTable if any
    if (DataTable.isDataTable('#' + tableContainer)) {
      var table = $('#' + tableContainer).DataTable();
      table.destroy(remove = false);
      $('#' + tableContainer).html('');
    };
    // Init datatable
    $('#' + tableContainer).DataTable({
      data: result.data.filter(e=>e.active),
      order: [[4,"desc"]],
      columns: result.header.columns.map(element => {
        return {
          'title': element['title'],
          'data': element['property'],
          'visible': element['visible']
        }
      }),
      columnDefs: [{
        targets: '_all',
        defaultContent: '--'
      }, { // Impacted entities
        targets: 0,
        render: function (data, type, row, meta) {
          let o = '';
          const key = (k) => `<span class="pull-left">${k}:</span>`;
          const val = (v) => `<span class="text-success pull-right">${v}</span>`;
          const obj = (o) => `<ul class="">${o}</ul>`;
          row.values.forEach(e => {
            Object.keys(e).forEach(k => {
              let v = e[k];
              o = o + '<li>' + key(k) + '&nbsp;' + val(v) + '</li>';
            })
          });
          return obj(o);
        }
      }, { // Severity
        targets: 1,
        render: function (data, type, row, meta) {
          switch (data) {
            case 'Critical':
              return '<p class="text-danger">' + data + '</p>';
            case 'Major':
              return '<p class="text-warning">' + data + '</p>';
            default:
              return '<p class="">' + data + '</p>';
          }
        }
      }, { // Alarm Date
        targets: 4,
        render: function (data, type, row, meta) {
          if (data) {return toISOStringUTC(data)};
        }
      }, { // Clear Date
        targets: 5,
        render: function (data, type, row, meta) {
          if (data) {return toISOStringUTC(data)};
        }
      }, { // Actions
        targets: 6,
        render: function (data, type, row, meta) {
          const btnShow = (uuid) => `<button class="show-alarm btn btn-info"     id="btnShow-${uuid}" data-id="${uuid}">Show</button>`;
          const btnAck = (uuid) => `<button class="clear-alarm btn btn-success" id="btnAck-${uuid}" data-id="${uuid}">Clear</button>`;
          const btnGrp = (btnA, btnB) => `<p class="bs-component">${btnA} ${btnB}</p>`;
          if (row.active) {
            return btnGrp(btnShow(row.uuid), btnAck(row.uuid));
          } else {
            return btnGrp(btnShow(row.uuid), '');
          }
        }
      }],
      "pageLength": 200
    });
  });
};

///////////////////////////////////////////////////////////////////
//                         TASK UTILS                            //
///////////////////////////////////////////////////////////////////

// showTaskCount - get task count, update DOM, refresh at interval
function showTaskCount(contextElement, countElement, refreshInterval) {
  var getTaskCount = function () {
    if ($(contextElement).attr('data-id') > 0) {
      crud('index','device_action_status_tasks_activecount').then(data=>{
        if (data.error) {return};
        if (data.data && data.data.activeTaskCount > 0) {
          $(countElement).addClass('text-danger');
        } else {
          $(countElement).removeClass('text-danger');
        }
      });
    }
  }
  getTaskCount();
  setInterval(getTaskCount, refreshInterval); 
};

// showTaskDetails get_item(task_details)
function showTaskDetails(id,modalElement,tableValidation,tableTasks,spinnerElement,refreshInterval) {
  var getTaskDetails = function () {
    $('#'+spinnerElement).show();
    crud('read','device_action_status_by_actionName',{'actionName':id}).then(result=>{
      $('#'+spinnerElement).hide();
      // Sub-tasks info
      if (result.data) {
        $('#' + tableTasks).html('');
        // table head
        let props = ['host-name', 'status', //'actionConfig',
          'currentActivity', 'activity'];
        let thead = '<tr>' + props.map((e) => `<th>${e}</th>`).join('') + '</tr>';
        $('#' + tableTasks).append(thead);
        // table rows
        result.data.forEach((o) => {
          let row = '<tr>' + props.map((e) => {
            switch (e) {
              case 'host-name':
                return '<td><p class="text-info">' + o[e] + '</p></td>';
              case 'status':
                if (o[e] == 'Success') {
                  return '<td><p class="text-success">' + o[e] + '</p></td>';
                } else {
                  return '<td><p class="text-warning">' + o[e] + '</p></td>';
                }
              case 'actionConfig':
                return '<td><textarea class="form-control" disabled>' + JSON.stringify(JSON.parse(o[e]), null, 2) + '</textarea></td>';
              case 'currentActivity':
                return '<td><p class="">' + o[e] + '</p></td>';
              case 'activity':
                return '<td><ul>' + o[e].map((i) => `<li>${i}</li>`).join('') + '</ul></td>';
              default:
                return;
            };
          }).join('') + '</tr>';
          $('#' + tableTasks).append(row);
        })
      };
    });
  }
  getTaskDetails();
};

///////////////////////////////////////////////////////////////////
//                         USER UTILS                          //
///////////////////////////////////////////////////////////////////

// clearUserSession
function clearUserSession(btnId,tenantId,rawId,uuid) {
  console.log('btnId='+btnId+' uuid='+uuid);
  let payload = {};
  let sessions = [];
  let sessionInfo = {'tenantId':tenantId,'uuid':uuid,'rawId':rawId};
  sessions.push(sessionInfo);
  payload['data'] = sessions;
  crud('delete','admin_user_removesessions',{'data':payload}).then(data=>{
    console.log(data);
    if (data.error) {
      console.log(data.error);
    } else {
      $('#'+btnId).hide()
    };
  });
};

// showUserSessions
function showUserSessions(modal,content,spinner) {
  let columns=[
    {'title':'Username','data':'rawUserName'},
    {'title':'Source IP','data':'sourceIp'},
    {'title':'Start time','data':'createDateTime'},
    {'title':'Last used','data':'lastAccessedTime'},
    {'title':'Actions','data':'dummy'},
    {'title':'UUID','data':'uuid','visible':false},
  ];
  const btnClear = (tenantId,rawId,uuid) => `<button id="btn-clear-${uuid}" class="clear-session btn btn-danger" data-tenantId="${tenantId}" data-rawId="${rawId}" data-uuid="${uuid}" >Clear</button>`;
  $('#' + spinner).show();
  crud('index','admin_user_activesessions').then(data=>{
    $('#' + spinner).hide();
    if (data.data) {
      //  existing DataTable if any
      if (DataTable.isDataTable('#userSessionsTable')) {
        let oldtable = $('#userSessionsTable').DataTable();
        oldtable.destroy(remove = true);
      };
      // Create new table
      $('#'+content).html('<table id="userSessionsTable" class="table table-striped" style="width:100%;"></table>');
      // Init datatable
      $('#userSessionsTable').DataTable({
        columns: columns,
        data: data.data,
        columnDefs: [{
          targets: '_all',
          defaultContent: '--'
        }, { // Start time
          targets: 2,
          render: function (data, type, row, meta) {
            if (data) {return toISOStringUTC(data)};
          }
        }, { // Last used
          targets: 3,
          render: function (data, type, row, meta) {
            if (data) {return toISOStringUTC(data)};
          }
        }, { // Actions
          targets: 4,
          render: function (data, type, row, meta) {
            return btnClear(row.tenantId,row.rawId,row.uuid);
          }
        }],
        "pageLength": 200,
      
      });
      modal.show();
    }
  });
};

///////////////////////////////////////////////////////////////////
//                         DEVICE UTILS                          //
///////////////////////////////////////////////////////////////////

// 'device_reboot': '/dataservice/device/action/reboot', # { "action": "reboot", "deviceType": "vedge", "devices": [{"deviceIP": "1.2.3.4","deviceId": "xxxxxxxx"}] }
function rebootDevice (btn,modal,content,spinner) {
  let ip = $(btn).attr('data-ip');
  let uuid = $(btn).attr('data-uuid');
  let type = $(btn).attr('data-type');
  $('#' + spinner).show();
  //console.log('reboot: ip='+ip+' uuid='+uuid+' type='+type);

  // device payload
  let dev = {};
  dev.deviceIP = ip;
  dev.deviceId = uuid;

  // device list payload
  let list = [];
  list.push(dev);

  // reboot payload
  let req = {};
  req.action  = "reboot";
  req.deviceType = type;
  req.devices = list;

  //console.log(req);
  crud('create','device_action_reboot',{'data':req}).then(data=>{
    $('#' + spinner).hide();
    if (data.error) {
      //console.log(data.error);
    } else {
      $(btn).hide();
    }
  });
  return;
}

// showDevices
function showDevices(url,urlCSV,vEdgesActiveTable,vEdgesPendingTable,controllersTable,nfvisTable,spinner) {
  // link CSV
  const linkCSV = (url,template,uuid) => {url = url.replace('TEMPLATE',template); url = url.replace('UUID',uuid); return url};
  // Button templates
  const dropDown = (title, color, buttons,ip) => `<div class="btn-group" role="group" aria-label="dropdown">
  <button type="button" class="btn ${color}">${title}</button>
  <div class="btn-group" role="group">
    <button id="btnGroupDrop1-${ip}" type="button" class="btn btn-primary dropdown-toggle" data-bs-toggle="dropdown" aria-haspopup="true" aria-expanded="false"></button>
    <div class="dropdown-menu" aria-labelledby="btnGroupDrop1-${ip}">
      ${buttons}
    </div>
  </div>
  </div>`;
  const btnReboot   = (type,ip,uuid) => `<button class="reboot dropdown-item text-warning"  data-type="${type}" data-ip="${ip}" data-uuid="${uuid}">Reboot</button>`;
  const btnSessions = (type,ip,uuid) => `<button class="sessions dropdown-item" data-type="${type}" data-ip="${ip}" data-uuid="${uuid}">Sessions</button>`;
  const btnCSV      = (href)         => `<a class="dropdown-item" href="${href}">Download CSV</a>`
  $('#' + spinner).show();
  // Get device list
  getURL(url).then(result=>{
    console.log(result);
    $('#' + spinner).hide();
    // Populate active vEdges
    $('#'+vEdgesActiveTable).DataTable({
      data: result.data.filter(element => {if ( element['deviceType'] == "vedge" && (/(ENCS|UCPE)/.test(element['uuid']) == false) ) {return element} } ),
      columns: result.columns,
      columnDefs: [{
        targets: '_all',
        defaultContent: '--'
      },{
        // Make hostname name clickable
        targets: 0,
        render: function (data, type, row, meta) {
          return '<a class="fw-bold" href="' + row.link + '">' + data + '</a>';
        }
        // Replace empty values
      },{
        targets: 1,
        render: function (data, type, row, meta) {
          // State
          if (data == 'green') {
            return '<i class="fas fa-circle" style="color:green;"></i>'
          }
          if (data == 'orange') {
            return '<i class="fas fa-circle" style="color:orange;"></i>'
          }
          if (data == 'red') {
            return '<i class="fas fa-circle" style="color:red;"></i>'
          }
        }
      },{
        // Reachability status
        targets: 7,
        render: function (data, type, row, meta) {
          if (row.reachability == 'reachable') {
            return '<p class="text-success">' + data + '</p>'
          } else {
            return '<p class="text-danger">' + data + '</p>'
          }
        }
      },{
        // Sync status
        targets: 8,
        render: function (data, type, row, meta) {
          if (row.configStatusMessage == 'In Sync') {
            return '<p class="text-success">' + data + '</p>'
          } else {
            return '<p class="text-warning">' + data + '</p>'
          }
        }
      },{
        // Cert status
        targets: 9,
        render: function (data, type, row, meta) {
          if (row.validity == 'valid') {
            return '<p class="text-success">' + data + '</p>'
          } else {
            return '<p class="text-warning">' + data + '</p>'
          }
        }
      },{
        // Control connections
        targets: 10,
        render: function (data, type, row, meta) {
          // warn if some sessions are missing (indicated by parenthesis in bfdSessions string)
          if ( row.controlConnections==0 ) {
            return '<p class="text-warning">' + data + '</p>'
          } else {
            return '<p class="text-success">' + data + '</p>'
          }
        }
      },{
        // BFD Sessions
        targets: 11,
        render: function (data, type, row, meta) {
          // warn if some sessions are missing (indicated by parenthesis in bfdSessions string)
          if ( /\(/.test(row.bfdSessions) ) {
            return '<p class="text-warning">' + data + '</p>'
          } else {
            return '<p class="text-success">' + data + '</p>'
          }
        }
      },{
        // OMP Peers
        targets: 12,
        render: function (data, type, row, meta) {
          // warn if some sessions are missing (indicated by parenthesis in bfdSessions string)
          if ( /\(/.test(row.ompPeers) ) {
            return '<p class="text-warning">' + data + '</p>'
          } else {
            return '<p class="text-success">' + data + '</p>'
          }
        }
      },{
        // Actions
        targets: 15,
        render: function (data, type, row, meta) {
          if (row.deviceType == 'vedge' && row.reachability == 'reachable') {
            return dropDown('Actions','btn-primary',btnReboot(row['deviceType'], row['system-ip'], row['uuid']) +  btnCSV( linkCSV(urlCSV, row['templateId'], row['uuid']) ));
          }
        }
      }],
      "pageLength": 200
    });
    // Populate NFVIS
    $('#'+nfvisTable).DataTable({
      data: result.data.filter(element => { if ( element['deviceType'] == "vedge" && (/(ENCS|UCPE)/.test(element['uuid']) == true) ) {return element}} ),
      columns: result.columns,
      columnDefs: [{
        targets: '_all',
        defaultContent: '--'
      },{
        // Make hostname name clickable
        targets: 0,
        render: function (data, type, row, meta) {
          return '<a class="fw-bold" href="' + row.link + '">' + data + '</a>';
        }
        // Replace empty values
      },{
        targets: 1,
        render: function (data, type, row, meta) {
          // State
          if (data == 'green') {
            return '<i class="fas fa-circle" style="color:green;"></i>'
          }
          if (data == 'orange') {
            return '<i class="fas fa-circle" style="color:orange;"></i>'
          }
          if (data == 'red') {
            return '<i class="fas fa-circle" style="color:red;"></i>'
          }
        }
      },{
        // Reachability status
        targets: 7,
        render: function (data, type, row, meta) {
          if (row.reachability == 'reachable') {
            return '<p class="text-success">' + data + '</p>'
          } else {
            return '<p class="text-danger">' + data + '</p>'
          }
        }
      },{
        // Sync status
        targets: 8,
        render: function (data, type, row, meta) {
          if (row.configStatusMessage == 'In Sync') {
            return '<p class="text-success">' + data + '</p>'
          } else {
            return '<p class="text-warning">' + data + '</p>'
          }
        }
      },{
        // Cert status
        targets: 9,
        render: function (data, type, row, meta) {
          if (row.validity == 'valid') {
            return '<p class="text-success">' + data + '</p>'
          } else {
            return '<p class="text-warning">' + data + '</p>'
          }
        }
      },{
        // Control connections
        targets: 10,
        render: function (data, type, row, meta) {
          // warn if some sessions are missing (indicated by parenthesis in bfdSessions string)
          if ( row.controlConnections==0 ) {
            return '<p class="text-warning">' + data + '</p>'
          } else {
            return '<p class="text-success">' + data + '</p>'
          }
        }
      },{
        // BFD Sessions
        targets: 11,
        render: function (data, type, row, meta) {
          // warn if some sessions are missing (indicated by parenthesis in bfdSessions string)
          if ( /\(/.test(row.bfdSessions) ) {
            return '<p class="text-warning">' + data + '</p>'
          } else {
            return '<p class="text-success">' + data + '</p>'
          }
        }
      },{
        // OMP Peers
        targets: 12,
        render: function (data, type, row, meta) {
          // warn if some sessions are missing (indicated by parenthesis in bfdSessions string)
          if ( /\(/.test(row.ompPeers) ) {
            return '<p class="text-warning">' + data + '</p>'
          } else {
            return '<p class="text-success">' + data + '</p>'
          }
        }
      },{
        // Actions
        targets: 15,
        render: function (data, type, row, meta) {
          if (row.deviceType == 'vedge' && row.reachability == 'reachable') {
            return dropDown('Actions','btn-primary',btnReboot(row['deviceType'], row['system-ip'], row['uuid']));
          }
        }
      }],
      "pageLength": 200
    });
    // Populate Controllers table
    const exclude_columns = ['controlConnections','bfdSessions','ompPeers','cpuLoadDisplay','memUsageDisplay'];
    $('#'+controllersTable).DataTable({
      data: result.data.filter(element => { if (element['deviceType'] != "vedge") {return element}  } ),
      columns: result.columns.filter(element => {
        let include = true;
        for(const col of exclude_columns){
          if (element.data == col) { include=false; }
        }
        if (include) {return element};
      } ),
      columnDefs: [{
        targets: '_all',
        defaultContent: '--'
      },{
        // Make hostname name clickable
        targets: 0,
        render: function (data, type, row, meta) {
          return '<p class="fw-bold" href="' + row.link + '">' + data + '</p>';
        }
        // Replace empty values
      },{
        targets: 1,
        render: function (data, type, row, meta) {
          // State
          if (data == 'green') {
            return '<i class="fas fa-circle" style="color:green;"></i>'
          }
          if (data == 'orange') {
            return '<i class="fas fa-circle" style="color:orange;"></i>'
          }
          if (data == 'red') {
            return '<i class="fas fa-circle" style="color:red;"></i>'
          }
        }
      },{
        // Reachability status
        targets: 7,
        render: function (data, type, row, meta) {
          if (row.reachability == 'reachable') {
            return '<p class="text-success">' + data + '</p>'
          } else {
            return '<p class="text-danger">' + data + '</p>'
          }
        }
      },{
        // Sync status
        targets: 8,
        render: function (data, type, row, meta) {
          if (row.configStatusMessage == 'In Sync') {
            return '<p class="text-success">' + data + '</p>'
          } else {
            return '<p class="text-warning">' + data + '</p>'
          }
        }
      },{
        // Cert status
        targets: 9,
        render: function (data, type, row, meta) {
          if (row.validity == 'valid') {
            return '<p class="text-success">' + data + '</p>'
          } else {
            return '<p class="text-warning">' + data + '</p>'
          }
        }
      },{
        // Actions
        targets: 10,
        render: function (data, type, row, meta) {
          let reboot = '' ;
          if (row.reachability == 'reachable') {
            reboot = btnReboot(row['deviceType'], row['system-ip'], row['uuid']) + ' ';
          }
          if (row['device-type'] == 'vmanage') {
            return dropDown('Actions','btn-primary',reboot + btnSessions(row['deviceType'], row['system-ip'], row['uuid']));
          } else {
              return dropDown('Actions','btn-primary',reboot);
          }
        }
      }],
      "pageLength": 200
    });
    // Populate vEdgesPendingTable
    $('#'+vEdgesPendingTable).DataTable({
      data: result.inactive.data,
      columns: [
        {'title':'UUID','data':'uuid','visible':true},
        {'title':'CFG Mode','data':'configOperationMode','visible':true},
        {'title':'CFG Status','data':'configStatusMessage','visible':true},
        {'title':'Log','data':'templateApplyLog','visible':true},
        {'title':'Cert status','data':'vedgeCertificateState','visible':true},
        {'title':'Cert validity','data':'validity','visible':true},
        {'title':'Upload source','data':'uploadSource','visible':false},
        {'title':'Model','data':'deviceModel','visible':false}
      ],
      columnDefs: [{
        targets: '_all',
        defaultContent: '--'
      },{
        // Make hostname name clickable
        targets: 0,
        render: function (data, type, row, meta) {
          return '<p class="fw-bold" href="' + row.link + '">' + data + '</p>';
        }
      },{
        // Template log
        targets: 3,
        render: function (data, type, row, meta) {
          if(data){
            logs = row.templateApplyLog;
            return logs.join('<br>');
          }
        }      
      }],
      "pageLength": 200
    });      
  });
};

// Fetch sdwan or running config from device
function showDeviceConfig(url,div) {
  let spinner = '#loader';
  $(spinner).show();
  const config = (data) =>  `<pre class="col-lg-12"><code class="language-cisco">${data}</code></pre>`;
  getURL(url).then(data=>{
    $(spinner).hide();
    if (data.config) {
      $('#'+div).html(config(data.config));
      hljs.highlightAll();
    } else {
      let alert = makeAlert('danger','Oops!','Request failed; please try again!',false);
      $('#'+div).html(alert);
    }
  });
};

// Device real time monitoring
function showDeviceActions(deviceId,data,selector) {
  const selectInput = (id,options) => `
        <!--<label for="${id}" class="form-label mt-4">${id}</label>-->
        <select id="${id}" name="${id}" class="selectpicker form-select form-control" data-live-search="true">${options}</select>`;
  const option = (name, action, object, deviceId) => `<option data-object="${object}" data-action="${action}" data-deviceId="${deviceId}">${name}</option>`;
  // Create options
  options = data.data.map(e=>{ 
       children = e.children.map(f=>{ return option(f.name,f.action,f.object,deviceId) }).join('\n');
       return children
    }).join('\n');
  // Create select
  select = selectInput('selectpicker-action',`<option></option>${options}`);
  $(selector).html(select);
  $('#selectpicker-action').selectpicker();
  // Attach event
  $('#selectpicker-action').change(function(){
    //$('#myTable').hide();
    $('#realtimeErrorContainer').html('');
    //$( "select option:selected" ).each(function() {
      $( "select.selectpicker option:selected" ).each(function() {
      let object = $(this).attr('data-object');
      let action = $(this).attr('data-action');
      let deviceId = $(this).attr('data-deviceid');
      // CRUD call
      $('#loader').show();
      crud(action,object,{'deviceId':deviceId}).then(result=>{
        $('#loader').hide();
        // Query error
        if (result.hasOwnProperty('error')) {
          $('#realtimeErrorContainer').html(makeAlert('warning','Oops',result.message,false));
          $('#myTable').hide();
          $('#realtimeErrorContainer').show();
        // Empty result
        } else if (result.data.length == 0) {
          $('#realtimeErrorContainer').html(makeAlert('info','No data','The query returned an empty result',false));
          $('#myTable').hide();
          $('#realtimeErrorContainer').show();
        // Show data
        } else {
          $('#realtimeErrorContainer').hide();
          $('#realtimeErrorContainer').html('');
          // Clear existing DataTable if any
          if (DataTable.isDataTable('#myTable')) {
            var table = $('#myTable').DataTable();
            table.destroy(remove = true);
            $('#myTableContainer').html('<div id="realtimeErrorContainer"></div><table id="myTable" class="table table-striped table-secondary" width="100%">');
          };
          // Init DataTable
          $('#myTable').show();
          $('#myTable').DataTable({
            data: result.data,
            columns: result.header.columns.map(e=>{return {'title':e.title,'data':e.property}}),
            columnDefs: [{
              targets: '_all',
              defaultContent: '-',
              render: function (data, type, row, meta) {
                let colName = meta.settings.aoColumns[meta.col].data;
                if (colName == 'lastupdated' || colName == 'time-date' || colName == 'uptime-date') {
                  return toISOStringUTC(data);
                } else {
                  return data;
                }
              }
            }]
          });
        };
      });
    });
  });
}