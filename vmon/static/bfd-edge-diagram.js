
// inspired from https://observablehq.com/@d3/bilevel-edge-bundling?collection=@d3/d3-hierarchy

function bfdEdgeDiagram(graph) {
  // Variables
  //////////////////////////////////////////////////////////////////////
  //var container = "#myEdgeContainer";
  var colorin = "#d62728";
  var colorout = "#2ca02c";
  var colornone = "#888"; //"#4682b4";
  var coloractive = "#3498db";
  var width = 800;
  var radius = width / 2;
  var line = d3.lineRadial()
    .curve(d3.curveBundle.beta(0.85))
    .radius(d => d.y)
    .angle(d => d.x);
  var tree = d3.cluster()
    .size([2 * Math.PI, radius - 100]);

  // Main 
  //////////////////////////////////////////////////////////////////////
  var data = load(graph);
  //console.log(data);
  return chart(data);
  //var node = chart(data);
  //$(container).html(node);

  // Process data
  //////////////////////////////////////////////////////////////////////
  function load(graph) {
    const { nodes, links } = graph;
    const groupById = new Map;
    const nodeById = new Map(nodes.map(node => [node.id, node]));

    for (const node of nodes) {
      let group = groupById.get(node.group);
      if (!group) groupById.set(node.group, group = { id: node.group, children: [] });
      group.children.push(node);
      node.targets = [];
    }

    for (const { source: sourceId, target: targetId } of links) {
      nodeById.get(sourceId).targets.push(targetId);
    }

    return { children: [...groupById.values()] };
  }

  // Link nodes
  //////////////////////////////////////////////////////////////////////
  function bilink(root) {
    const map = new Map(root.leaves().map(d => [d.data.id, d]));
    for (const d of root.leaves()) d.incoming = [], d.outgoing = d.data.targets.map(i => [d, map.get(i)]);
    for (const d of root.leaves()) for (const o of d.outgoing) o[1].incoming.push(o);
    //console.log(root);
    return root;
  }

  // Draw chart from processed data
  //////////////////////////////////////////////////////////////////////
  function chart(data) {

    const root = tree(bilink(d3.hierarchy(data)
      .sort((a, b) => d3.ascending(a.height, b.height) || d3.ascending(a.data.id, b.data.id))));

    const svg = d3.create("svg")
    .attr("height","100%")
    //.attr("width","auto")
      .attr("viewBox", [-width / 2, -width / 2, width, width]);

    const node = svg.append("g")
      .attr("font-family", "sans-serif")
      .attr("font-size", 10)
      .selectAll("g")
      .data(root.leaves())
      .join("g")
      .attr("transform", d => `rotate(${d.x * 180 / Math.PI - 90}) translate(${d.y},0)`)
      .append("text")
      .attr("fill", colornone)
      .attr("dy", "0.31em")
      .attr("x", d => d.x < Math.PI ? 6 : -6)
      .attr("text-anchor", d => d.x < Math.PI ? "start" : "end")
      .attr("transform", d => d.x >= Math.PI ? "rotate(180)" : null)
      //.text(d => d.data.id)
      .text(d => d.data.name)
      //.attr("class", "policy-sequence")
      .each(function (d) { d.text = this; })
      .on("mouseover", overed)
      .on("mouseout", outed)
      //.call(text => text.append("title").text(d => `${d.data.id}
      .call(text => text.append("title").text(d => `TLOC Info:
systemip ${d.data.systemIp}
color ${d.data.color}
site ${d.data.site}
pref ${d.data.preference}
restrict ${d.data.restrict}
group ${d.data.group}
ifStatus ${d.data.state}

BFD Sessions:
${d.outgoing.length} outgoing
${d.incoming.length} incoming`));

    const link = svg.append("g")
      .attr("stroke", colornone)
      .attr("stroke-opacity", 0.5)
      .attr("fill", "none")
      .selectAll("path")
      .data(root.leaves().flatMap(leaf => leaf.outgoing))
      .join("path")
      //.style("mix-blend-mode", "multiply")
      //.attr("data-state",d => d.data)
      .attr("d", ([i, o]) => line(i.path(o)))
      .each(function (d) { d.path = this; });

    function overed(event, d) {
      //link.style("mix-blend-mode", null);
      d3.select(this).attr("font-weight", "bold").attr("fill",coloractive);
      d3.selectAll(d.incoming.map(d => d.path)).attr("stroke", colorin).raise();
      d3.selectAll(d.incoming.map(d => d.path)).attr("stroke-opacity", 2).raise();
      d3.selectAll(d.incoming.map(([d]) => d.text)).attr("fill", colorin).attr("font-weight", "bold");
      d3.selectAll(d.outgoing.map(d => d.path)).attr("stroke", colorout).raise();
      d3.selectAll(d.outgoing.map(d => d.path)).attr("stroke-opacity", 2).raise();
      d3.selectAll(d.outgoing.map(([, d]) => d.text)).attr("fill", colorout).attr("font-weight", "bold");
    }

    function outed(event, d) {
      //link.style("mix-blend-mode", "multiply");
      d3.select(this).attr("font-weight", null).attr("fill",colornone);
      d3.selectAll(d.incoming.map(d => d.path)).attr("stroke", colornone);
      d3.selectAll(d.incoming.map(d => d.path)).attr("stroke-opacity", 0.5).raise();
      d3.selectAll(d.incoming.map(([d]) => d.text)).attr("fill", colornone).attr("font-weight", null);
      d3.selectAll(d.outgoing.map(d => d.path)).attr("stroke", colornone);
      d3.selectAll(d.outgoing.map(d => d.path)).attr("stroke-opacity", 0.5).raise();
      d3.selectAll(d.outgoing.map(([, d]) => d.text)).attr("fill", colornone).attr("font-weight", null);
    }

    return svg.node();
  }
}
