require.undef('d3_utils');

define('d3_utils', ['d3'], function (d3) {
    function scatter(element, data, field_x, field_y, field_class, label_fn) {

        var margin = {top: 20, right: 20, bottom: 30, left: 40},
            width = 600 - margin.left - margin.right,
            height = 400 - margin.top - margin.bottom;

        // SVG
        var svg = d3.select(element)
            .append('svg')
            .attr("width", width + margin.left + margin.right)
            .attr("height", height + margin.top + margin.bottom)
            .append('g')
            .attr("transform", "translate(" + margin.left + "," + margin.top + ")");;

        // Scales
        var colorScale = d3.scaleOrdinal(d3.schemeCategory10);
        var xScale = d3.scaleLinear()
            .domain([
                d3.min(data, function (d) {return d[field_x]}),
                d3.max(data, function (d) {return d[field_x]})
            ])
            .range([0, width])
        var yScale = d3.scaleLinear()
            .domain([
                d3.min(data, function (d) {return d[field_y]}),
                d3.max(data, function (d) {return d[field_y]})
            ])
            .range([height, 0])

        // X-axis
        var xAxis = d3.axisBottom(xScale)
            .ticks(5)
        // Y-axis
        var yAxis = d3.axisLeft()
            .scale(yScale)
            .ticks(5)
        // Circles
        var circles = svg.selectAll('circle')
            .data(data)
            .enter()
            .append('circle')
            .attr('cx', function (d) {
                return xScale(d[field_x])
            })
            .attr('cy', function (d) {
                return yScale(d[field_y])
            })
            .attr('r', '3')
            .attr('stroke', 'black')
            .attr('stroke-width', 0.5)
            .attr('fill', function (d) {
                return colorScale(d[field_class])
            })
            .on('mouseover', function () {
                d3.select(this)
                    //.transition()
                    //.duration(500)
                    .attr('r', 5)
                    .attr('stroke-width', 1)
            })
            .on('mouseout', function () {
                d3.select(this)
                    //.transition()
                    //.duration(500)
                    .attr('r', 3)
                    .attr('stroke-width', 1)
            })
            .append('title') // Tooltip
            .text(label_fn)
        // X-axis
        svg.append('g')
            .attr('class', 'axis')
            .attr('transform', 'translate(0,' + height + ')')
            .call(xAxis)
            .append('text') // X-axis Label
            .attr('class', 'label')
            .attr('y', -10)
            .attr('x', width)
            .attr('dy', '.71em')
            .style('text-anchor', 'end')
            .text('X')
        // Y-axis
        svg.append('g')
            .attr('class', 'axis')
            .call(yAxis)
            .append('text') // y-axis Label
            .attr('class', 'label')
            .attr('transform', 'rotate(-90)')
            .attr('x', 0)
            .attr('y', 5)
            .attr('dy', '.71em')
            .style('text-anchor', 'end')
            .text('Y');
        
          // draw legend
          var legend = svg.selectAll(".legend")
              .data(colorScale.domain())
            .enter().append("g")
              .attr("class", "legend")
              .attr("transform", function(d, i) { return "translate(0," + i * 20 + ")"; });

          // draw legend colored rectangles
          legend.append("rect")
              .attr("x", width - 18)
              .attr("width", 18)
              .attr("height", 18)
              .style("fill", colorScale);

          // draw legend text
          legend.append("text")
              .attr("x", width - 24)
              .attr("y", 9)
              .attr("dy", ".35em")
              .style("text-anchor", "end")
              .text(function(d) { return d;})
    }

    return {
        scatter: scatter
    };
});
