
// inspired from https://observablehq.com/@d3/arc-diagram

function arcDiagram(data) {
  //console.log(data);
  // Variables
  //////////////////////////////////////////////////////////////////////
  margin = { top: 20, right: 20, bottom: 20, left: 20 };
  fontFamily = 'Roboto,sans-serif';
  fontSize = '0.8rem';
  width = 1400;
  target = "#myArcContainer"; // target DOM element
  select = "#myArcSelect"; // select container
  step = 18;                   // vertical spacing
  r = 4;                       // circle size
  xPosition = 220;             // x position for circles 
  $(target).html('')
  // Load data
  //////////////////////////////////////////////////////////////////////
  function bfd(data) {
    // Map nodes data
    const nodes = data.nodes.map(({ id, group, name }) => ({
      id,
      sourceLinks: [],
      targetLinks: [],
      group,
      name
    }));
    const nodeById = new Map(nodes.map(d => [d.id, d]));
    // Map links data
    //const links = data.links.map(({ source, target, state, color, value }) => ({
    const links = data.links.filter(element => { if ( element.target != undefined ) {return element}}).map(({ source, target, state, color, value }) => ({
      source: nodeById.get(source),
      target: nodeById.get(target),
      state: state,
      color: color,
      value
    }));
    // Update links data
    for (const link of links) {
      const { source, target, state, value } = link;
      if (target != undefined) {
        source.sourceLinks.push(link);
        target.targetLinks.push(link);
      } else {
        console.log(link);
      }
    }
    return { nodes, links };
  };

  // arc line
  //////////////////////////////////////////////////////////////////////
  function arc(d) {
    const y1 = y(d.source.id);
    const y2 = y(d.target.id);
    const r = Math.abs(y2 - y1) / 2;
    return `M${xPosition},${y1}A${r},${r} 0,0,${y1 < y2 ? 1 : 0} ${xPosition},${y2}`;
  };

  // Define sort options
  //////////////////////////////////////////////////////////////////////
  const options = [
    { name: "Order by name", value: (a, b) => d3.ascending(a.name, b.name) },
    { name: "Order by group", value: (a, b) => d3.ascending(a.group, b.group) },
    { name: "Order by degree", value: (a, b) => d3.sum(b.sourceLinks, l => l.value) + d3.sum(b.targetLinks, l => l.value) - d3.sum(a.sourceLinks, l => l.value) - d3.sum(a.targetLinks, l => l.value) }
  ];

  // Define select form
  //////////////////////////////////////////////////////////////////////
  const form = `<form style="display: flex; align-items: center; min-height: 33px;" class="form-control">
                  <select class="form-select form-select-sm" name=mySelect>${options.map(o => '<option>' + o.name + '</option>')}
                  </select></form>`;


  // Main loop
  //////////////////////////////////////////////////////////////////////
  // Inject select form
  $(select).html(form);

  // Attach change event to form
  $('select[name=mySelect]').change(function () {
    // get sorting formula from selected option
    let formula = options[this.selectedIndex].value;
    // Calculate new Y positions for all nodes
    y.domain(bfd(data).nodes.sort(formula).map(d => d.id));
    // Init transition
    const t = svg.transition()
      .duration(750);
    // Transition text
    label.transition(t)
      .delay((d, i) => i * 20)
      .attrTween("transform", d => {
        const i = d3.interpolateNumber(d.y, y(d.id));
        return t => `translate(${xPosition},${d.y = i(t)})`;
      });
    // Transition lines
    path.transition(t)
      .duration(750 + bfd(data).nodes.length * 20)
      .attrTween("d", d => () => arc(d));
    // Transition overlay
    overlay.transition(t)
      .delay((d, i) => i * 20)
      .attr("y", d => y(d.id) - step / 2);
  });

  // Calculate diagram height
  const height = (bfd(data).nodes.length - 1) * step + margin.top + margin.bottom;

  // Init SVG
  vbWidth = width + margin.left + margin.right;
  vbHeight = height + margin.top + margin.bottom;
  const svg = d3.select(target)
    .append("svg")
  //const svg = d3.create("svg")
    .attr("viewBox", "0,0," + vbWidth + "," + vbHeight)
    .attr("width", vbWidth)
    .attr("height", vbHeight);

  // color scale
  const color = d3.scaleOrdinal(bfd(data).nodes.map(d => d.group)
    .sort(d3.ascending),
//    d3.schemeSet3);
    d3.schemePastel1);

  // A linear scale to position the nodes on the Y axis
  const y = d3.scalePoint(bfd(data).nodes.map(d => d.id)
    .sort(d3.ascending), [margin.top, height - margin.bottom]);

  // Add Device
  const label = svg.append("g")
    .attr("font-family", fontFamily)
    .attr("font-size", fontSize)
    .attr("text-anchor", "end")
    .selectAll("g")
    // Loop on nodes
    .data(bfd(data).nodes)
    .join("g")
    // Move to start position
    .attr("transform", d => `translate(${xPosition},${d.y = y(d.id)})`)
    // Add hostname
    .call(g => g.append("text")
      .attr("x", -6)
      .attr("dy", "0.35em")
      .attr("fill", d => d3.lab(color(d.group)).darker(2))
      // Set id
      .attr("id", d => 'text_' + d.name)
      // Insert custom Text label
      .text(d => d.name + '[' + d.id + '][' + d.group + ']'))
    // Add circle
    .call(g => g.append("circle")
      .attr("r", r)
      // Set group color
      .attr("fill", d => color(d.group))
      // Set Id
      .attr("id", d => 'circle_' + d.name));

  // Add Path
  const path = svg.insert("g", "*")
    .attr("fill", "none")
    .attr("stroke-opacity", 0.6)
    .attr("stroke-width", 1.5)
    .selectAll("path")
    // Loop on links
    .data(bfd(data).links)
    .join("path")
    // Set id
    .attr("id", d => 'path_' + d.source.name + '_' + d.target.name)
    // Insert source hostname
    .attr("source", d => d.source.name)
    // Insert target hostname
    .attr("target", d => d.target.name)
    // Insert BFD link status
    .attr("state", d => d.state)
    // Set group color
    .attr("stroke", d => d.source.group === d.target.group ? color(d.source.group) : "#aaa")
    // Calculate Arc
    .attr("d", d => {
      start = y(d.source.id)
      end = y(d.target.id)
      return [arc(d)]
        //return ['M', xPosition, start,
        //  'A',
        //  (start - end)/2, ',',
        //  (start - end)/2, 0, 0, ',',
        //  start < end ? 1 : 0, xPosition, ',', end]
        .join(' ');
    });

  // Add transparent overlay for mouse interaction
  const overlay = svg.append("g")
    .attr("fill", "none")
    .attr("pointer-events", "all")
    .selectAll("rect")
    // Loop on nodes
    .data(bfd(data).nodes)
    .join("rect")
    // Set id
    .attr("id", d => 'overlay_' + d.name)
    // Insert hostname attribute for future mouse interactions
    .attr("hostname", d => d.name)
    .attr("width", width - margin.left - xPosition)
    .attr("height", step)
    .attr("y", d => y(d.id) - step / 2)
    // Attach "mouse over" event
    .on("mouseover", function (d) {
      // Switch diagram to "hover mode"
      svg.classed("hover", true);
      // Toggle primary class on active device
      var hostname = $(this).attr('hostname');
      $("#text_" + hostname).toggleClass("primary", true);
      // Follow paths from active device
      $('path[source="' + hostname + '"]').each(function (index) {
        var path = $(this);
        // Toggle path as primary
        path.toggleClass("primary", true);
        // Toggle target device as secondary
        target = path.attr('target');
        $("#text_" + target).toggleClass("secondary", true);
      });
      // Follow reverse paths to active device
      $('path[target="' + hostname + '"]').each(function (index) {
        var path = $(this);
        // Toggle path as primary
        path.toggleClass("primary", true);
      });
    })
    // Attach "mouse out" event
    .on("mouseout", function (d) {
      svg.classed("hover", false);
      $('path').toggleClass("primary", false);
      $('text').toggleClass("primary", false);
      $('text').toggleClass("secondary", false);
    });
  //return svg.node();
  //$(target).html(svg.node);
}
