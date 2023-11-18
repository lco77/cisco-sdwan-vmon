
// Get policy data - vManage RAW data
async function getPolicyData(id,flavor) {
  // Define policy flavor to API object mappings
  const flavorMap = {
    'vsmart':                   'template_policy_vsmart_definition_by_policyId',
    'vedge':                    'template_policy_vedge_definition_by_policyId',
  };
  // Fetch policy data
  let data = await crud('read',flavorMap[flavor],{'id':id});
  // Add missing info
  data.id = id;
  data.object = flavorMap[flavor];
  // Remove unecessary keys
  data = deleteKey(data,'references');
  data = deleteKey(data,'referenceCount');
  data = deleteKey(data,'activatedId');
  data = deleteKey(data,'isActivatedByVsmart');
  data = deleteKey(data,'lastUpdated');
  data = replaceKey(data,'policyName','name');
  data = replaceKey(data,'policyDescription','description');
  //console.log(data);
  return data;
}

// Get policy definitions data - vManage RAW data
async function getPolicyDefinitionData(definitions) {
  // Define definition type to API object mappings
  const definitionMap = {
    'control':                      'template_policy_definition_control',
    'appRoute':                     'template_policy_definition_approute',
    'vedgeRoute':                   'template_policy_definition_vedgeroute',
    'data':                         'template_policy_definition_data',
    'cflowd':                       'template_policy_definition_cflowd',
    'zoneBasedFW':                  'template_policy_definition_zonebasedfw',
};
  const objects = definitions.map(definition=>{ return {'object':policyMap[definition['type']],'id':definition['definitionId']} });
  let data = await Promise.all(objects.map(async e => { 
    const data = await crud('index',e['object'],{'id':e['id']});
    return data
   }));
  // Remove unecessary keys
  data = deleteKey(data,'references');
  data = deleteKey(data,'referenceCount');
  data = deleteKey(data,'activatedId');
  data = deleteKey(data,'isActivatedByVsmart');
  data = deleteKey(data,'lastUpdated');
  data = deleteKey(data,'definitionId');
  //console.log(data);
  return data;
}

// Get policy list data from definition sequences - vManage RAW data
async function getPolicyListData(definitions) {
  // Find list objects to resolve
  let objects = findListObjects(definitions);
  // Get list objects
  objects = deleteKey(objects,'id');
  let data = await Promise.all(objects.map(async e => { 
    const data = await crud('index',e['object']);
    return data
   }));

  // Remove unecessary keys
  data = deleteKey(data,'references');
  data = deleteKey(data,'referenceCount');
  data = deleteKey(data,'activatedId');
  data = deleteKey(data,'isActivatedByVsmart');
  data = deleteKey(data,'lastUpdated');
  data = replaceKey(data,'listId','id');
  //console.log(data);
  return data;
};

// Find list objects - used by getPolicyListData()
function findListObjects(o) {
  // Define list type to API object mappings
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
  let a = [];
  if (Array.isArray(o)) {
    // recurse on array elements
    o.forEach(e=>{ let b = findListObjects(e); a.push(...b); });
  } else {
    Object.keys(o).forEach(k=>{
      if (typeof o[k] == 'object') {
          // recurse if another object is found
          let b = findListObjects(o[k]);
          a.push(...b);
      } else {
        // lookup "field" key for known list type
        if (o[k].toLowerCase() in listMap && 'ref' in o) {
          let isMissing = true;
          a.forEach(e => {
            if (o['ref'] == e['id']) { isMissing = false};
          });
          // New element: push to array
          if (isMissing) {
            let b = { 'object':listMap[o[k].toLowerCase()], 'id':o['ref'] };
            a.push(b);
          };
        }
      }
    });
  };
  // Filter out duplicates
  const ids = a.map(o => o.object)
  const filtered = a.filter(({object}, index) => !ids.includes(object, index + 1))
  return filtered;
};

// render SVG diagram - old version with collapsible elements
// inspired from  https://observablehq.com/@d3/collapsible-tree
function policyDiagram(data) {
  var margin = { top: 20, right: 20, bottom: 20, left: 200 };
  var fontFamily = 'Roboto,sans-serif';
  var fontSize = '0.7rem';
  var width = 1600;
  var dx = 13
  var dy = width / 10

  tree = d3.tree().nodeSize([dx, dy]);
  diagonal = d3.linkHorizontal().x(d => d.y).y(d => d.x);

  const root = d3.hierarchy(data);

  //root.x0 = dy / 2;
  root.x0 = 100;
  root.y0 = 0;
  root.descendants().forEach((d, i) => {
    d.id = i;
    d._children = d.children;
    //if (d.depth && d.data.name.length !== 7) d.children = null;
  });

  const svg = d3.create("svg")
  //const svg = d3.select(target).append("svg")
    //.attr("viewBox", [-margin.left, -margin.top, width, dx])
    .attr("viewBox", [0, 0, width, dx])
    .attr("font-family", fontFamily)
    .attr("font-size", fontSize)
    //.style("font", "10px sans-serif")
    .style("user-select", "none");
  //.append("g")
  //.attr("transform", "translate(100,100)");


  const gLink = svg.append("g")
    .attr("fill", "none")
    .attr("stroke", "#555")
    .attr("stroke-opacity", 0.4)
    .attr("stroke-width", 1.5);

  const gNode = svg.append("g")
    .attr("cursor", "pointer")
    .attr("pointer-events", "all");

  function update(source) {
    const duration = d3.event && d3.event.altKey ? 2500 : 250;
    const nodes = root.descendants().reverse();
    const links = root.links();

    // Compute the new tree layout.
    tree(root);

    let left = root;
    let right = root;
    root.eachBefore(node => {
      if (node.x < left.x) left = node;
      if (node.x > right.x) right = node;
    });

    const height = right.x - left.x + margin.top + margin.bottom;

    const transition = svg.transition()
      .duration(duration)
      .attr("viewBox", [-margin.left, left.x - margin.top, width, height])
      .tween("resize", window.ResizeObserver ? null : () => () => svg.dispatch("toggle"));

    // Update the nodes…
    const node = gNode.selectAll("g")
      .data(nodes, d => d.id);

    // Enter any new nodes at the parent's previous position.
    const nodeEnter = node.enter().append("g")
      .attr("transform", d => `translate(${source.y0},${source.x0})`)
      .attr("fill-opacity", 0)
      .attr("stroke-opacity", 0)
      .on("click", (event, d) => {
        d.children = d.children ? null : d._children;
        update(d);
      });

    nodeEnter.append("circle")
      .attr("r", 4)
      .attr("fill", d => d._children ? "#555" : "#999")
      .attr("stroke-width", 10);

    nodeEnter.append("text")
      .attr("dy", "0.31em")
      .attr("x", d => d._children ? -6 : 6)
      .attr("text-anchor", d => d._children ? "end" : "start")
      .attr("class", d => d.data.class)
      .attr("data-bs-toggle", "tooltip")
      .attr("data-bs-placement", "top")
      .attr("title", d => d.data.tooltip)
      .text(d => d.data.name);
      //.clone(true).lower()
      //.attr("stroke-linejoin", "round")
      //.attr("stroke-width", 1)
      //.attr("stroke", "white");

    // Transition nodes to their new position.
    const nodeUpdate = node.merge(nodeEnter).transition(transition)
      .attr("transform", d => `translate(${d.y},${d.x})`)
      .attr("fill-opacity", 1)
      .attr("stroke-opacity", 1);

    // Transition exiting nodes to the parent's new position.
    const nodeExit = node.exit().transition(transition).remove()
      .attr("transform", d => `translate(${source.y},${source.x})`)
      .attr("fill-opacity", 0)
      .attr("stroke-opacity", 0);

    // Update the links…
    const link = gLink.selectAll("path")
      .data(links, d => d.target.id);

    // Enter any new links at the parent's previous position.
    const linkEnter = link.enter().append("path")
      .attr("d", d => {
        const o = { x: source.x0, y: source.y0 };
        return diagonal({ source: o, target: o });
      });

    // Transition links to their new position.
    link.merge(linkEnter).transition(transition)
      .attr("d", diagonal);

    // Transition exiting nodes to the parent's new position.
    link.exit().transition(transition).remove()
      .attr("d", d => {
        const o = { x: source.x, y: source.y };
        return diagonal({ source: o, target: o });
      });

    // Stash the old positions for transition.
    root.eachBefore(d => {
      d.x0 = d.x;
      d.y0 = d.y;
    });
  }

  update(root);

  return svg.node();
}

// Create filter form
function policyForm(id,data,callback) {
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
  const select = (id,label,options,obj,property,col,cssclass) => `
      <div class="form-group ${col}">
      <label for="${id}" class="form-label mt-4 ${cssclass}">${label}</label>
      <select id="${id}" name="${id}" data-object="${obj}" data-property="${property}" class="form-select form-control">${options}</select>
      </div>`;
  const input = (id,label,property,cssclass) => `
      <div class="form-group col-lg-2">
      <label for="${id}" class="form-label mt-4 ${cssclass}">${label}</label>
      <input id="${id}" type="text" name="${id}" data-property="${property}" class="form-control">
      </div>`;    
  const btn = (action,label,col) => `
      <div class="form-group ${col}">
      <label class="form-label mt-4">&nbsp;</label>
      <a class="btn btn-success form-control ${action}" href="#">${label}</a>
      </div>`;
  const options = (o) => {
      output = '<option value=""></option>';
      Object.keys(o).sort().forEach(e=>{
          output = output + '<option value="'+e+'">'+o[e]+'</option>';
      });
      return output;
  };
  // Options data
  let definitionNames = {};
  let definitionTypes = {};
  let sequenceTypes = {};
  let sequenceNames = {};
  function findObject(data) {
    Object.keys(data).forEach(k=>{
      if (k == 'children' && Array.isArray(data.children)) {
        data.children.forEach(child=>{findObject(child)});
      }
      if (k == 'object') {
        switch (data[k]) {
          case 'definition':
            definitionTypes[data.type] = data.type; 
            definitionNames[data.name]  = data.name; 
            break;
          case 'sequence':
            sequenceTypes[data.type] = data.type; 
            sequenceNames[data.name]  = data.name; 
            break;
        }
      }
    });
  };
  findObject(data);
  // Make form
  let inputs = select('definitionType','Definition Type',options(definitionTypes),'definition','type','col-lg-2','text-muted')
             + select('definitionName','Definition Name',options(definitionNames),'definition','name','col-lg-3','text-muted')
             + select('sequenceType',  'Sequence Type',  options(sequenceTypes),  'sequence',  'type','col-lg-2','text-muted')
             + select('sequenceName',  'Sequence Name',  options(sequenceNames),  'sequence',  'name','col-lg-3','text-muted')
             //+ input('iproutePrefix','Prefix','route-destination-prefix','text-muted')
             + btn('policyRefresh','Filter','col-lg-1');
  // Callback function meant to register event on refresh button
  callback(form(id,inputs));
};

// Read filter form & filter data
function policyFilter(data,selector) {
  // Read formdata
  var filter = {'sequence':{},'definition':{}};
  $(selector+' select,'+selector+' input').each(function(e){
      let val      = $(this).val();
      let object   = $(this).attr('data-object');
      let property = $(this).attr('data-property');
      filter[object][property] = val;
  });
  // Filter data
  function filterObject(data,filter) {
    //console.log(filter);
    let filtered = null;
    let keep = true;
    let type;
    let name;
    switch (data.object) {
      case 'definition':
        type = filter.definition.type;
        name = filter.definition.name;
        //console.log('definition data: type=' + data.type + ' name=' + data.name);
        //console.log('definition filter: type=' + type + ' name=' + name);
        if (type && type != '' && data.type != type) {keep=false; console.log('->remove type');}
        if (name && name != '' && data.name   != name) {keep=false; console.log('->remove name');}
        break;
      case 'sequence':
        type = filter.sequence.type;
        name = filter.sequence.name;
        //console.log('sequence data: type=' + data.type + ' name=' + data.name);
        //console.log('sequence filter: type=' + type + ' name=' + name);
        if (type && type != '' && data.type != type) {keep=false; console.log('->remove type');}
        if (name && name != '' && data.name   != name) {keep=false; console.log('->remove name');}
        break;
    };
    if (keep) {
      filtered = data;
      if ('children' in data && Array.isArray(data.children)) {
        filtered.children = data.children.filter(child=>{
          //console.log('-> processing child: ' + child.object + ' type=' + child.type + ' name=' + child.name);
          return filterObject(child,filter);
        });
      }
    }
    return filtered;
  };

  let filtered = filterObject(data,filter);
  //console.log(filtered);
  return filtered;
};

// render SVG diagram
function policySVG(data) {
  // set the dimensions and margins of the diagram
  const margin = { top: 10, right: 0, bottom: 10, left: 0 };
  const width  = 1800;

  //  assigns the data to a hierarchy using parent-child relationships
  let nodes = d3.hierarchy(data);

  // Dynamic layout
  const padding = 1; // horizontal padding for first and last column
  const dx = 20; // vertical spacing
  //const dy = width / (nodes.height + padding);
  const dy = 300; // horizontal spacing
  d3.tree().nodeSize([dx, dy])(nodes);

  // Center the tree.
  let x0 = Infinity;
  let x1 = -x0;
  nodes.each(d => {
  if (d.x > x1) {x1 = d.x};
  if (d.x < x0) {x0 = d.x};
  });
  const height = x1 - x0 + dx * 2;  

  //console.log(nodes);

  // create svg object
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
      .attr("transform","translate(50,0)"); // offset diagram from viewport
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
      //.text(d => d.data.name == 'root' ? '' : `${d.data.type} ${d.data.object}: ${d.data.name}`)
      .text(d => d.depth == 0 ? 'Policy' : `${d.data.type} ${d.data.object}: ${d.data.name}`)
      // mouseover/mouseout handling
      .each(function (d) { d.text = this; })
      .on("mouseover", overed)
      .on("mouseout", outed)
      .call(text => text.append("title").text(d => {
        return `${d.data.description}`;
          //if (d.data.type == 'route') {
          //    var tooltip = 'Data:\n'
          //                + Object.keys(d.data).map(e=>`${e} = ${d.data[e]}`).join('\n');
          //    return tooltip;
          //}
      }));
      //.call(text => text.append("title").text(d => `Title: ${d.data.id}`));
  
  // callback functions on mouseover & mouseout
  function overed(event, d) {};
  function outed(event, d) {};

  // Return SVG diagram
  return svg.node();
};