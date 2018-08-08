// NOTE: NOT YET FULLY MIGRATED

/**
for integration
remember to include:
==================== HEAD ====================

<script src="https://d3js.org/d3.v4.min.js"></script>
<script src="/static/js/rt_graphview.js"></script>



<!-- -- -- GRAPH VIEW | SVG -- -- -->
==================== BODY ====================

<div class="container">
  <div class="panel panel-default">
    <div id="cid_info" class="container">
    </div>
    <div class="container">
      <svg width="600" height="500"></svg>
    </div>
  </div>
</div>


NOTE ON THE IMPLEMENTATION:
=============================================
The method *renderDocConcepts* makes a JSON request
for the graph relating to document $docid.

JSON response format, example:
{
  "status": "OK",
  "links": [
    {
      "relation": "related", 
      "source": "26288-1", 
      "target": "26290-0"
    }, 
    ...
    {
      "source": "11328-4", 
      "target": "V"
    }
  ], 
  "nodes": [
    {
      "group": 6, 
      "id": "26288-1", 
      "type": "concept"
    }, 
    ...
    {
      "group": 0, 
      "id": "V", 
      "type": "thsys"
    }, 
    ...
  ],
  ... 
  }
}

TODO this 

Author: Martin Toepfer (ZBW), 2017-2018
*/

// const PATH_GRAPHAPI_PREFIX = "/api/graph/";
const ID_GI = "#graph_info"; // div that is used to show error messages etc.
const ID_GC = "#graph_container"; // div that contains a SVG elem for the graph
const SEL_GSVG = ID_GC + " svg";

function render_graph(docid, graphapi_path) {
    // console.log("render graph @ " + docid)
    $(SEL_GSVG).data("docid", docid).empty();
    var svg = d3.select(SEL_GSVG),
        width = +svg.attr("width")-20,
        height = +svg.attr("height")-20;
    var top_radius = (Math.min(width, height) / 2) - 50;
    var center_x = width / 2;
    var center_y = height / 2;
    
    // create simulation and init forces
    var force_mb = d3.forceManyBody().strength(function(n) {
        // make negative force of kategory nodes stronger than descriptor nodes
        return n.type=='descriptor'? -40 : -200;
    });
    var force_link = d3.forceLink().id(function(d) { return d.id; });
    var strength_k = function(n) {
        return n.type=='descriptor'? 0 : 15;
    };
    /* */
    var forceXk = d3.forceX(center_x).strength(function(n) {
        return n.type=='descriptor'? -2 : 0;
    }); // alternative forceRadial ?
    var forceYk = d3.forceY(center_y).strength(function(n) {
        return n.type=='descriptor'? -10 : 0;
    }); // alternative forceRadial ?
    //
    var force_radialK = d3.forceRadial(50, center_x, center_y).strength(strength_k)
    // TODO put descriptors onto circles, too ... like an onion :)
    var simulation = d3.forceSimulation()
        .force("link", force_link)
        .force("charge", force_mb)
        .force("collide", d3.forceCollide(25))
        // .force("center", d3.forceCenter(center_x, center_y))
        .force("radialK", force_radialK);
        //.force("fXk", forceXk)
        //.force("fYk", forceYk);
    
    var json_url = graphapi_path; // + docid
    
    var tick_fun = function (link, node, node_label) {
        link
            .attr("x1", function(d) { return d.source.x; })
            .attr("y1", function(d) { return d.source.y; })
            .attr("x2", function(d) { return d.target.x; })
            .attr("y2", function(d) { return d.target.y; });
        node_label
            .attr("x", function(d) {
               return d.x - (d.type=="descriptor"? 2 : 5);
            })
            .attr("y", function(d) { 
               return d.y - (d.type=="descriptor"? 6 : 12);
            });
        node
            .attr("cx", function(d) { return d.x; })
            .attr("cy", function(d) { return d.y; });
    };
    
    
    var json_handle = function(error, graph) {
      if (error || graph.status != 'OK') {
          $(ID_GI).html(
              $('<div class="bg-danger">Backend-Error</div>')
          ).removeClass("hidden");
          throw error;
      } else {
          $(ID_GI).addClass("hidden");
      }
      var top_total = 7;
      var label_fetcher = function(concept_id) {
          // graph.subj_info[d.id]['label'] : d.id
          if (concept_id in graph.labels) {
              return graph.labels[concept_id];
          } 
          return concept_id;
      };
      var link = svg.append("g")
          .attr("class", "z-c-rel-link")
        .selectAll("line")
        .data(graph.links)
        .enter().append("line")
          .attr("stroke", "black")
          .attr("stroke-width", function(d) { return 1; }); // Math.sqrt(d.value);

      // TODO var colmap = 
      var node = svg.append("g")
          .attr("class", "z-c-node")
        .selectAll("circle")
        .data(graph.nodes)
        .enter().append("circle")
          .attr("r", function(d) {return d.type=="descriptor"? 5 : 10;})
          .attr("fill", "#AAA"); // function(d) {return colmap[d.group]});
      /*
      node.on("mouseover", function(d){
          var cid = d.id;
          if (cid in graph.labels) {
            var label = label_fetcher(cid);
            var msg = cid + " " + label;
            $(ID_GI).text(msg); // debugging info...
          }
      });
      */
      node.append("title").text(function(d) { return d.id; });
      
      var node_label = svg.append("g")
          .attr("class", "z-c-label")
        .selectAll("text")
        .data(graph.nodes)
        .enter().append("text");
      node_label
        .text( function (d) {
          var lab_ = d.type=='thsys'? d.group : label_fetcher(d.id);
          return lab_;
        })
        .attr("font-size", function (d) {
          return d.type=="descriptor"?  "12px" : "15px";
        });
      
      simulation
          .nodes(graph.nodes)
          .on("tick", function() {tick_fun(link, node, node_label);});
      simulation.force("link")
          .links(graph.links);
    }
    // finally, make the json request which then renders the graph
    d3.json(json_url, json_handle);
}

