
// inspired from  https://observablehq.com/@d3/collapsible-tree

// Create form
function iprouteForm(id,data,callback) {
    // Form components
    const form = (id,inputs) => `
        <form id="${id}">
        <fieldset>
        <div class="form-group row">
        ${inputs}
        </div>
        </fieldset>
        </form>
        <br>`;
    const select = (id,label,options,property,cssclass) => `
        <div class="form-group col-lg-2">
        <label for="${id}" class="form-label mt-4 ${cssclass}">${label}</label>
        <select id="${id}" name="${id}" data-property="${property}" class="form-select form-control">${options}</select>
        </div>`;
    const input = (id,label,property,cssclass) => `
        <div class="form-group col-lg-2">
        <label for="${id}" class="form-label mt-4 ${cssclass}">${label}</label>
        <input id="${id}" type="text" name="${id}" data-property="${property}" class="form-control">
        </div>`;    
    const btn = (action,label) => `
        <div class="form-group col-lg-1">
        <label class="form-label mt-4">&nbsp;</label>
        <a class="btn btn-success form-control ${action}" href="#">${label}</a>
        </div>`;
    const options = (o) => {
        output = '<option value=""></option>';
        Object.keys(o).forEach(e=>{
            output = output + '<option value="'+e+'">'+o[e]+'</option>';
        });
        return output;
    };
    // Options data
    let vpns = {};
    let familys = {};
    let protocols = {};
    let nexthops = {};
    data.forEach(e=>{
        Object.keys(e).forEach(k=>{
            switch (k) {
                case 'routing-instance-name':
                    vpns[e[k]] = e[k];
                    break;
                case 'rib-address-family':
                    familys[e[k]] = e[k];
                    break;
                case 'route-source-protocol':
                    protocols[e[k]] = e[k];
                    break;
                case 'next-hop-next-hop-address':
                    nexthops[e[k]] = e[k] + ' [' + e['next-hop-outgoing-interface'] + ']';
                    break;
                };
        });
    });
    // Make form
    let inputs = select('iprouteVpn','VRF',options(vpns),'routing-instance-name','text-success')
               + select('iprouteFamily','Address family',options(familys),'rib-address-family','text-info')
               + select('iprouteProtocol','Protocol',options(protocols),'route-source-protocol','text-danger')
               + select('iprouteNextHop','Next Hop',options(nexthops),'next-hop-next-hop-address','text-warning')
               //+ input('iprouteNextHop','Next Hop','next-hop-next-hop-address','text-warning')
               + input('iproutePrefix','Prefix','route-destination-prefix','text-muted')
               + btn('iprouteRefresh','Filter');
    // Update DOM
    //$(selector).html(form(id,inputs));
    // Callback function meant to register event on refresh button
    callback(form(id,inputs));
}

// Read filters & refresh
// filter output
// {property:value, property:value, ...}
function iprouteFilter(data,selector) {
    // Read formdata
    var filter = {};
    $(selector+' select,'+selector+' input').each(function(e){
        let property = $(this).attr('data-property');
        let val = $(this).val();
        filter[property] = val;
    });
    // Filter data
    var filtered = data.filter(e=>{
        let keep = true;
        Object.keys(filter).forEach(f=>{
            if (filter[f]!='' && !e[f].includes(filter[f])) {keep=false};
        });
        if (keep) {return e};
    });
    return filtered;
};

// Make data hierarchy - parent[property] > child[property]:
//   > root[root]
//   > routing-instance-name[]
//   > rib-address-family[]
//   > route-source-protocol[route-route-preference]
//   > next-hop-next-hop-address[next-hop-outgoing-interface]
//   > route-destination-prefix[route-metric]
function iprouteHierarchy(data) {
    var nodes = [];
    var nexthops = {};
    var protocols = {};
    var familys = {};
    var vpns = {};
    // node IDs
    const vpnId      = (e) => e['routing-instance-name'];
    const familyId   = (e) => [vpnId(e),e['rib-address-family']].join('-');
    const protocolId = (e) => [familyId(e),e['route-source-protocol']].join('-');
    const nexthopId  = (e) => [protocolId(e),e['next-hop-next-hop-address'],e['next-hop-outgoing-interface']].join('-');
    const routeId    = (e) => [nexthopId(e),e['route-destination-prefix']].join('-');
    // node template
    const node = (id,obj,parentId,type,name,property,color,stroke,size) => {
        let value = {
            'id': id,
            'object': obj,
            'parentId': parentId,
            //'name': name,
            'name': property == '' ? name : name + ' [' + property + ']',
            'type': type,
            //'property': property ? property : '',
            'color':color,
            'stroke':stroke,
            'size':size,
        };
        return value;
    };
    // Root node
    nodes.push(node('root',{},'','root','root','','white','#ebebeb',10));
    // add Route nodes
    data.forEach(e => {
        // Init vpn node & update link data
        if (!vpns.hasOwnProperty(vpnId(e))) {
            vpns[vpnId(e)] = {'node': node(vpnId(e),e,'root','vpn',e['routing-instance-name'],'','#00bc8c','#ebebeb',9), 'children':{}};
        };
        vpns[vpnId(e)]['children'][familyId(e)] = '';
        
        // Init family node & update link data
        if (!familys.hasOwnProperty(familyId(e))) {
            familys[familyId(e)] = {'node': node(familyId(e),e,vpnId(e),'family',e['rib-address-family'],'','#3498db','#ebebeb',8), 'children':{}};
        };
        familys[familyId(e)]['children'][protocolId(e)] = '';

        // Init protocol node & update link data
        if (!protocols.hasOwnProperty(protocolId(e))) {
            protocols[protocolId(e)] = {'node': node(protocolId(e),e,familyId(e),'protocol',e['route-source-protocol'],'','#e74c3c','#ebebeb',7), 'children':{}};
        };
        protocols[protocolId(e)]['children'][nexthopId(e)] = '';

        // Init nexthop node & update link data
        if (!nexthops.hasOwnProperty(nexthopId(e))) {
            nexthops[nexthopId(e)] = {'node': node(nexthopId(e),e,protocolId(e),'nexthop',e['next-hop-next-hop-address'],e['next-hop-outgoing-interface'],'#f39c12','#ebebeb',6), 'children':{}};
        };
        nexthops[nexthopId(e)]['children'][routeId(e)] = '';

        // Add route to node list
        nodes.push(node(routeId(e),e,nexthopId(e),'route',e['route-destination-prefix'],e['route-route-preference']+'/'+e['route-metric'],'#adb5bd','#ebebeb',5));
    });
    
    // Add vpn nodes
    Object.keys(vpns).forEach(e=>{nodes.push(vpns[e]['node']);});
    
    // Add family nodes
    Object.keys(familys).forEach(e=>{nodes.push(familys[e]['node']);});
 
    // Add protocol nodes
    Object.keys(protocols).forEach(e=>{nodes.push(protocols[e]['node']);});

    // Add nexthop nodes
    Object.keys(nexthops).forEach(e=>{nodes.push(nexthops[e]['node']);});
    //console.log({'nodes':nodes});
    return nodes;
};

function iprouteSVG(data,selector) {
    // set the dimensions and margins of the diagram
    const margin = { top: 10, right: 0, bottom: 10, left: 100 };
    //const width  = 1400 - margin.left - margin.right;
    const width  = 1400;
    //const height = 1200 - margin.top - margin.bottom;

    // declares a tree layout and assigns the size
    //const treemap = d3.tree().size([height, width]);
    //  assigns the data to a hierarchy using parent-child relationships
    let nodes = d3.stratify()(data);
    // maps the node data to the tree layout
    //nodes = treemap(nodes);
    //console.log(nodes);

// Dynamic layout
const padding = 1; // horizontal padding for first and last column
const dx = 20;
const dy = width / (nodes.height + padding);
d3.tree().nodeSize([dx, dy])(nodes);
// Center the tree.
let x0 = Infinity;
let x1 = -x0;
nodes.each(d => {
  if (d.x > x1) {x1 = d.x};
  if (d.x < x0) {x0 = d.x};
});
const height = x1 - x0 + dx * 2;  
console.log(nodes);

    // append the svg object to the body of the page
    //const svg = d3.select(selector).append("svg")
    const svg = d3.create("svg")
        .attr("viewBox", [-dy * padding / 2, x0 - dx, width, height])
        //.attr("width", width + margin.left + margin.right)
        .attr("width", width)
        //.attr("height", height + margin.top + margin.bottom)
        .attr("height", height)
        .attr("style", "max-width: 100%; height: auto; height: intrinsic;");

    // appends a 'group' element to 'svg'
    // moves the 'group' element to the top left margin
    const g = svg.append("g")
        .attr("transform","translate(-90,0)");
        //.attr("transform","translate(" + margin.left + "," + margin.top + ")");

    // adds the links between the nodes
    const link = g.selectAll(".link")
        .data(nodes.descendants().slice(1))
        .enter().append("path")
        .attr("class", "link")
        .style("stroke", d => d.data.color)
        .attr("d", d => {
            return "M" + d.y + "," + d.x
                + "C" + (d.y + d.parent.y) / 2 + "," + d.x
                + " " + (d.y + d.parent.y) / 2 + "," + d.parent.x
                + " " + d.parent.y + "," + d.parent.x;
        });

    // adds each node as a group
    const node = g.selectAll(".node")
        .data(nodes.descendants())
        .enter().append("g")
        .attr("class", d => "node" + (d.children ? " node--internal" : " node--leaf"))
        .attr("transform", d => "translate(" + d.y + "," + d.x + ")");

    // adds the circle to the node
    node.append("circle")
        .attr("r", d => d.data.size)
        .style("stroke", d => d.data.stroke)
        .style("fill", d => d.data.color);

    // adds the text to the node
    node.append("text")
        .attr("dy", ".35em")
        .attr("x", d => d.children ? (d.data.size + 5) * -1 : d.data.size + 5)
        .attr("y", d => d.children ? -(d.data.size + 5) : d.data.size - 5)
        .attr("class","node")
        .style("text-anchor", d => d.children ? "end" : "start")
        .style("fill", d => d.data.color)
        .text(d => d.data.name == 'root' ? '' : d.data.name)
        // mouseover/mouseout handling
        .each(function (d) { d.text = this; })
        .on("mouseover", overed)
        .on("mouseout", outed)
        .call(text => text.append("title").text(d => {
            if (d.data.type == 'route') {
                var tooltip = 'Data:\n'
                            + Object.keys(d.data.object).map(e=>`${e} = ${d.data.object[e]}`).join('\n');
                return tooltip;
            }
        }));
        //.call(text => text.append("title").text(d => `Title: ${d.data.id}`));
    
    // callback functions on mouseover & mouseout
    function overed(event, d) {};
    function outed(event, d) {};

    // Return SVG diagram
    return svg.node();
};