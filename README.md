# mikegraph
 Python Package for Graphing DHI MIKE URBAN database. Requires ArcPy through ArcMap or ArcGIS Pro.

<b>To install:</b>

```
python -m pip install https://github.com/enielsen93/mikegraph/tarball/master
```


<b>Example</b>
```
import mikegraph

graph = mikegraph.Graph(r"C:\MIKE Model.mdb")

graph.map_network()

targets = graph.find_upstream_nodes(["DU09",'D16060R','OU02'])

total_catchments = []
for target in targets:
    catchments = graph.find_connected_catchments(target)
    for catchment in catchments:
        total_catchments.append(catchment.MUID)
        
```
