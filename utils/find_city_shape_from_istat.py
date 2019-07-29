import geopandas as gp
import matplotlib.pyplot as plt

df = gp.read_file("Dati_istat/Com01012019_g_WGS84.shp")
df.head()

df = df[df.COD_PROV == 37][["COMUNE", "geometry"]].reset_index(drop=True)

neighbours = []

cm = plt.get_cmap('RdBu')

for i, comune in df.iterrows():
    tmp_neighbours = df[~df.geometry.disjoint(comune.geometry)].COMUNE.tolist()
    neighbours.append([name for name in tmp_neighbours if comune.COMUNE != name])


df["neighbours"] = neighbours
df["color"] = [cm(1. * i / len(df), alpha=0.75) for i in range(len(df))]

df["empire_geometry"] = df.geometry
df["empire_neighbours"] = df.neighbours
df["empire_color"] = df.color

df = df.rename(columns={"COMUNE": "Territory"})
df["Empire"] = df.Territory

df.set_index("Territory", drop=True, inplace=True)
df.head()

df.to_pickle("bologna.pickle")
