import geopandas as gp
import matplotlib.pyplot as plt

df = gp.read_file("Com01012019_g_WGS84.shp")
df.head()

bolo = df[df.COD_PROV == 37][["COMUNE", "geometry"]].reset_index(drop=True)

neighbours = []

cm = plt.get_cmap('RdBu')

for i, comune in bolo.iterrows():
    tmp_neighbours = bolo[~bolo.geometry.disjoint(comune.geometry)].COMUNE.tolist()
    neighbours.append([name for name in tmp_neighbours if comune.COMUNE != name])
bolo["neighbours"] = neighbours

bolo["color"] = [cm(1. * i / len(bolo), alpha=0.75) for i in range(len(bolo))]
bolo.head()
bolo.to_pickle("Bologna.pickle")