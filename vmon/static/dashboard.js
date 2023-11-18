
// Error template
///////////////////////////////////////////////////////////////////////////////
const errorAlert = (id, error) => `
<div id="alert-${id}" class="alert alert-danger">
  <strong>${error}</strong>
</div>
`;

// Server template
///////////////////////////////////////////////////////////////////////////////
const serverContainer = (id, server, description) => `
<!-- ${id} -->
<div class="row" id="${id}">
    <h4 class="text-info">${description}</h4>
</div>`;

// Chart container template
///////////////////////////////////////////////////////////////////////////////
const chartContainer = (id) => `
<canvas id="chart-${id}">
</canvas>`;

// Spinner template
///////////////////////////////////////////////////////////////////////////////
const spinner = (id) => `
<div id="spinner-${id}" class="spinner-border text-warning" role="status" style="width: 8rem; height: 8rem;" >
    <span class="visually-hidden">Loading...</span>
</div>`;

// Status card template
///////////////////////////////////////////////////////////////////////////////
const statusCard = (id, title) => `
<!-- card-${id} -->
<div id="card-${id}" class="card text-white bg-dark border-light md-1" style="height:13rem; width: 13rem; max-width: 13rem; margin-right: 1rem;">
  <div class="card-header text-center">${title}</div>
    <div class="card-body">
        <div class="text-center">
            ${spinner(id)}
            ${chartContainer(id)}
            ${errorAlert(id,'')}
        </div>
  </div>
</div>`;

// Main function to create dashboard
///////////////////////////////////////////////////////////////////////////////
async function makeDashboard (api,id,server,description,dashboardContainer) {
    var idServerContainer = 'server-' + id;
    var dashboardComponents = [
        {'order': 5, 'name': 'inventory_health',    'title': 'vEdge Inventory'    },
        //{'order': 6, 'name': 'certificate_health',  'title': 'Certificates'       },
        {'order': 3, 'name': 'control_health',      'title': 'Control Connections'},
        {'order': 4, 'name': 'vedge_health',        'title': 'vEdge Hardware'       },
        {'order': 0, 'name': 'vmanage_health',      'title': 'vManage Status'     },
        {'order': 1, 'name': 'site_health',         'title': 'Site Reachability'  },
        {'order': 2, 'name': 'reachability_health', 'title': 'Device Reachability'},
    ];
    // Create Fabric container
    $('#'+dashboardContainer).append(serverContainer(idServerContainer,server,description));
    // Create Dashboard layout
    dashboardComponents.sort((a,b)=>(a.order>b.order?1:-1)).map((e=>{$('#'+idServerContainer).append(statusCard(id+'-'+e.name,e.title));}));
    // Render dashboard components
    dashboardComponents.map( async e => {
        const myid = id;
        const url = api + id + '?object=' + e.name;
        const element = e;
        await renderComponents(url,myid,element);
    });
}

// renderComponents - route rendering requests to appropriate function
///////////////////////////////////////////////////////////////////////////////
async function renderComponents(url,id,component) {
    //let cardId = 'card-' + id + '-' + component.name;
    let cardId = id + '-' + component.name;
    // Call appropriate renderer
    switch (component.name) {
        case 'inventory_health':
            renderInventoryHealth(cardId,url,component);
            break;
        case 'certificate_health':
            renderCertificateHealth(cardId,url,component);
            break;
        case 'control_health':
            renderControlHealth(cardId,url,component);
            break;
        case 'vedge_health':
            renderVedgeHealth(cardId,url,component);
            break;
        case 'vmanage_health':
            renderVmanageHealth(cardId,url,component);
            break;
        case 'site_health':
            renderSiteHealth(cardId,url,component);
            break;
        case 'reachability_health':
            renderReachabilityHealth(cardId,url,component);
            break;
        default:
            break;
    };
};

// Chart config - standard config for most dashboard components
///////////////////////////////////////////////////////////////////////////////
function chartConfig (dataset) { 
    return {
        type: 'doughnut',
        data: dataset,
        options: {
            plugins: {
                title: {display: false,},
                legend: {display: false,}
            }
        }
    }
};

// showSpinner
///////////////////////////////////////////////////////////////////////////////
function showSpinner(id) {
    // show spinner
    $('#chart-'+id).hide();
    $('#alert-'+id).hide();
    $('#spinner-'+id).show();
};

// showAlert
///////////////////////////////////////////////////////////////////////////////
function showAlert(id,error) {
    // show alert
    $('#alert-'+id ).replaceWith(errorAlert(id,error));
    $('#spinner-'+id).hide();
    $('#chart-'+id).hide();
    $('#alert-'+id ).show();
};

// showChart
///////////////////////////////////////////////////////////////////////////////
function showChart(id) {
    // show chart
    $('#alert-'+id ).hide();
    $('#spinner-'+id).hide();
    $('#chart-'+id).show();
};

// renderInventoryHealth
///////////////////////////////////////////////////////////////////////////////
function renderInventoryHealth (id,url,component) {
    // Chart dataset
    const dataset = {
        labels: ['deployed','staging','available','denied'],
        datasets: [{
            label: component.name,
            data: [],//[deployed,staging,available,denied],
            backgroundColor: ['#00bc8c','#3498db','#adb5bd','#e74c3c'], // [green, blue, grey, red]
            hoverOffset: 4
        }],
    };
    // Init chart without data
    var chart = new Chart(document.getElementById('chart-'+id),  chartConfig(dataset) );
    // Get data
    var getData = function() {
        showSpinner(id);
        // get data
        getURL(url).then(json=>{
            if (json.error) {showAlert(id,json.error); return; };
            showChart(id);
            let data = json.data;  
            // Compute values
            let total      = data.filter( (e) => { if (e.name == "Total"     ) { return e } } )[0].value;
            let deployed   = data.filter( (e) => { if (e.name == "Deployed"  ) { return e } } )[0].value;
            let authorized = data.filter( (e) => { if (e.name == "Authorized") { return e } } )[0].value;
            let staging    = data.filter( (e) => { if (e.name == "Staging"   ) { return e } } )[0].value;
            let denied = total - authorized;
            let available = total - deployed - staging - denied;
            // Update chart
            chart.data.datasets[0].data = [deployed,staging,available,denied];
            chart.update();
        });
        //};
   }
   getData();
   setInterval(getData, updateInterval);
}

// renderCertificateHealth
///////////////////////////////////////////////////////////////////////////////
function renderCertificateHealth (id,url,component) {
    // Chart dataset
    const dataset = {
        labels: ['invalid','warning'],
        datasets: [{
            label: component.name,
            data: [], //[invalid, warning],
            backgroundColor: ['#f39c12','#e74c3c'], // orange, red
            hoverOffset: 4
        }],
    };
    // Init chart without data
    var chart = new Chart(document.getElementById('chart-'+id),  chartConfig(dataset) );
    // Get data
    var getData = function() {
        showSpinner(id);
        // get data
        getURL(url).then(json=>{
            if (json.error) {showAlert(id,json.error); return; };
            showChart(id);
            let data = json.data[0]; 
            // Compute values
            let invalid = data.invalid;
            let warning = data.warning;
            // Update chart
            chart.data.datasets[0].data = [invalid, warning];
            chart.update();
        });
    }
    getData();
    setInterval(getData, updateInterval);
}

// renderControlHealth
///////////////////////////////////////////////////////////////////////////////
function renderControlHealth (id,url,component) {
    // Chart dataset
    const dataset = {
        labels: ['full','partial', 'down'],
        datasets: [{
            label: component.name,
            data: [], //[full, partial, down],
            backgroundColor: ['#00bc8c','#f39c12','#e74c3c'], // green, orange, red
            hoverOffset: 4
        }],
    };
    // Init chart without data
    var chart = new Chart(document.getElementById('chart-'+id),  chartConfig(dataset) );
    // Get data
    var getData = function() {
        showSpinner(id);
        // get data
        getURL(url).then(json=>{
            if (json.error) {showAlert(id,json.error); return; };
            showChart(id);
            let data = json.data[0].statusList;
            // Compute values
            let full    = data.filter( (e) => { if (e.name == "Control up"     ) { return e } } )[0].count;
            let partial = data.filter( (e) => { if (e.name == "Partial"        ) { return e } } )[0].count;
            let down    = data.filter( (e) => { if (e.name == "Control down"   ) { return e } } )[0].count;
            // Update chart
            chart.data.datasets[0].data = [full, partial, down];
            chart.update();
        });
    }
    getData();
    setInterval(getData, updateInterval); 
}

// renderVedgeHealth
///////////////////////////////////////////////////////////////////////////////
function renderVedgeHealth (id,url,component) {
    // Chart dataset
    const dataset = {
        labels: ['normal','warning', 'error'],
        datasets: [{
            label: component.name,
            data: [], //[normal, warning, error],
            backgroundColor: ['#00bc8c','#f39c12','#e74c3c'], // green, orange, red
            hoverOffset: 4
        }],
    };
    // Init chart without data
    var chart = new Chart(document.getElementById('chart-'+id),  chartConfig(dataset) );
    // Get data
    var getData = function() {
        showSpinner(id);
        // get data
        getURL(url).then(json=>{
            if (json.error) {showAlert(id,json.error); return; };
            showChart(id);
            let data = json.data[0].statusList;
            // Compute values
            let normal   = data.filter( (e) => { if (e.name == "normal"  ) { return e } } )[0].count;
            let warning  = data.filter( (e) => { if (e.name == "warning" ) { return e } } )[0].count;
            let error    = data.filter( (e) => { if (e.name == "error"   ) { return e } } )[0].count;
            // Update chart
            chart.data.datasets[0].data = [normal, warning, error];
            chart.update();
        });
    }
    getData();
    setInterval(getData, updateInterval); 
}

// renderVmanageHealth
///////////////////////////////////////////////////////////////////////////////
function renderVmanageHealth (id,url,component) {
    // Chart dataset
    const dataset = {
        labels: ['up','down'],
        datasets: [{
            label: component.name,
            data: [], //[up, down],
            backgroundColor: ['#00bc8c','#e74c3c'], // green, red
            hoverOffset: 4
        }],
    };
    // Init chart without data
    var chart = new Chart(document.getElementById('chart-'+id),  chartConfig(dataset) );
    // Get data
    var getData = function() {
        showSpinner(id);
        // get data
        getURL(url).then(json=>{
            if (json.error) {showAlert(id,json.error); return; };
            showChart(id);
            let data = json.data[0];
            // Compute values
            let down = data.statusList[0].count;
            let up = data.count - down;
            // Update chart
            chart.data.datasets[0].data = [up, down];
            chart.update();
        });
    }
    getData();
    setInterval(getData, updateInterval); 
}

// renderSiteHealth
///////////////////////////////////////////////////////////////////////////////
function renderSiteHealth (id,url,component) {
    // Chart dataset
    const dataset = {
        labels: ['full','partial', 'down'],
        datasets: [{
            label: component.name,
            data: [], //[full, partial, down],
            backgroundColor: ['#00bc8c','#f39c12','#e74c3c'], // green, orange, red
            hoverOffset: 4
        }],
    };
    // Init chart without data
    var chart = new Chart(document.getElementById('chart-'+id),  chartConfig(dataset) );
    // Get data
    var getData = function() {
        showSpinner(id);
        // get data
        getURL(url).then(json=>{
            if (json.error) {showAlert(id,json.error); return; };
            showChart(id);
            let data = json.data[0].statusList;
            // Compute values
            let full    = data.filter( (e) => { if (e.name == "Full WAN Connectivity"    ) { return e } } )[0].count;
            let partial = data.filter( (e) => { if (e.name == "Partial WAN Connectivity" ) { return e } } )[0].count;
            let down    = data.filter( (e) => { if (e.name == "No WAN Connectivity"      ) { return e } } )[0].count;
            // Update chart
            chart.data.datasets[0].data = [full, partial, down];
            chart.update();
        });
    }
    getData();
    setInterval(getData, updateInterval); 
}

// renderReachabilityHealth
///////////////////////////////////////////////////////////////////////////////
function renderReachabilityHealth (id,url,component) {
    // Chart dataset
    const dataset = {
        labels: ['vEdge up','vEdge down', 'vSmart up', 'vSmart down','vBond up','vBond down'],
        datasets:     [{
            label: 'vEdge reachability',
            data: [], //[vedge.up, vedge.down],
            backgroundColor: ['#00bc8c','#e74c3c'], // green, red
        },{
            label: 'vSmart reachability',
            data: [], //[vsmart.up, vsmart.down],
            backgroundColor: ['#00bc8c','#e74c3c'], // green, red
        },{
            label: 'vBond reachability',
            data: [], //[vbond.up, vbond.down],
            backgroundColor: ['#00bc8c','#e74c3c'], // green, red
        }],
    };
    // Special config for multi layer pie chart
    const config = {
        type: 'pie',
        data: dataset,
        options: {
          responsive: true,
          plugins: {
            legend: {display:false},
            tooltip: {
              callbacks: {
                label: function(context) {
                  const labelIndex = (context.datasetIndex * 2) + context.dataIndex;
                  return context.chart.data.labels[labelIndex] + ': ' + context.formattedValue;
                }
              }
            }
          }
        },
      };
    // Init chart without data
    var chart = new Chart(document.getElementById('chart-'+id),  config );
    // Get data
    var getData = function() {
        showSpinner(id);
        // get data
        getURL(url).then(json=>{
            if (json.error) {showAlert(id,json.error); return; };
            showChart(id);
            let data = json.data;
            // Compute values
            let vedge = {};
            let vsmart = {};
            let vbond = {};
            data.forEach((e)=>{
                switch (e.name) {
                    case 'vSmart':
                        vsmart.up = e.count;
                        vsmart.down = e.statusList[0].count;
                        break;
                    case 'WAN Edge':
                        vedge.up = e.count;
                        vedge.down = e.statusList[0].count;
                        break;
                    case 'vBond':
                        vbond.up = e.count;
                        vbond.down = e.statusList[0].count;
                        break;
                    default:
                        break;
                }   
            });
            // Update chart
            chart.data.datasets[0].data = [vedge.up, vedge.down];
            chart.data.datasets[1].data = [vsmart.up, vsmart.down];
            chart.data.datasets[2].data = [vbond.up, vbond.down];
            chart.update();
        });
    }
    getData();
    setInterval(getData, updateInterval); 
}
