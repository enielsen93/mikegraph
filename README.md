# mikegraph
 Python Package for Graphing DHI MIKE URBAN database. Requires ArcPy through ArcMap or ArcGIS Pro.

<b>To install:</b>

```
python -m pip install https://github.com/enielsen93/mikegraph/tarball/master
```


## Example:
```
import mikegraph

# Creates graph of Mike Urban Database
graph = mikegraph.Graph(r"C:\MIKE Model.mdb")
graph.map_network()

# Finds nodes that all lead to 'DU09','D16060R','OU02'
targets = graph.find_upstream_nodes(["DU09",'D16060R','OU02'])

total_catchments = []
total_area = 0
total_impervious_area = 0
total_reduced_area = 0

# Loops through every node that lead to 'DU09','D16060R','OU02'
for target in targets:
    # Finds all catchments that are connected to nodes
    catchments = graph.find_connected_catchments(target)

    # Loops through every catchment connected to nodes, summarizes areas
    for catchment in catchments:
        total_catchments.append(catchment.MUID)
        total_area += catchment.area
        total_impervious_area += catchment.impervious_area
        total_reduced_area += catchment.reduced_area

print("Catchments that lead to nodes ('%s:')", ("', '".join(total_catchments)))
print("MUID IN ('%s')" % ("','".join(total_catchments)))

print("%d catchments with a total of %1.1f ha, %1.1f impervious ha and %1.1f reduced ha" % (len(total_catchments),
                                                                                            total_area/1e4,
                                                                                            total_impervious_area/1e4,
                                                                                            total_reduced_area/1e4))
```
