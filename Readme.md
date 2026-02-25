
# Fish dataset

This Readme documents the notebooks here for generating an input dataset for
ray-finned fish points for CVoL.

**FULL DISCLOSURE ON USE OF AI**

During the process of creating, maintaining, updating, and expanding these
notebooks, I increasingly used AI-assisted coding tools, in particular Claude
Sonnet 4.6. While these tools are far from perfect, I found them to be an
incredible resource for code analysis, review, and adding features. No data
was directly ingested or manipulated via AI.

Modifications to spherical-scatterplot-relaxation were performed using
Claude Sonnet 4.6.

**NOTEBOOKS**

The notebooks here are meant to be run in sequence, based on the 3 number prefix
on each one. Successive notebooks rely on data created by previous ones. The
starting point for the entire pipeline is a Newick-formatted tree downloaded
from TimeTree.org, using "fish" for the group of taxa, selecting
"Actinopterygii", and then "species". As of the writing of this document, there
were 15143 species in the tree.

The data cleaning notebook (101) is tailored to the tree downloaded at the time
of writing. An updated tree with new taxa (how often are new species of fish
identified?) may require modifications to the cleaning code.

##  1. Input Data Tree

Get species-level tree from Timetree.org (or genus-level if that's better, as
with insects). This is pre-fetched and stored in the git repo here. You can
update as you see fit, but you may need to fix up the cleaning code (101).

Output file: `ray-finned fishes_species.nwk`

## 2. Data cleaning. 
`101 Cleaning Actinopterygii species timetree with ete.ipynb` 

Make a "clean" species-level tree where the tips are all valid genus-species
binomials, and a CSV taxonomy lookup with order and family for every taxon.

Also make an order-level tree that will serve as a "scaffold" to graft species
level points onto later. This is constructed by selecting a random taxon in each
order and pruning the tree to keep only those taxa (one per order). The leaves
are then renamed to the given order and the tree is saved.
    
Outputs:

    output/Actinopterygii_species_with_order.nwk
    output/Actinopterygii_order_level.nwk
    output/Actinopterygii_genus_order_family_taxon.csv

`102 Plotting Actinopterygii tree.Rmd`

This R Markdown notebook uses ggtree to better visualize the tree. With 15000+
leaves, it's still pretty darn messy. Not sure how useful this is, but it's
included here. Not essential for the "pipeline".

## 3. Make a distance matrix.
`104 Genus tree distance matrix from tree.Rmd`

`105 Species tree distance matrix from tree.ipynb`

This is a species-level distance matrix generated from the tree file. It
contains tip-to-tip distances for all taxa. This can also be done in R with a
single call, but switching back and forth between environments is a pain. The
python uses Wandrille's sped-up method, but the R code contains some additional
statistical metrics and runs a lot faster. The distance matrices are nearly
identical and are functionally equivalent - there may be some differences in
precision, etc but it doesn't matter here.

Outputs:

    output/Actinopterygii_tree_distance_matrix_py.csv
    output/Actinopterygii_tree_distance_matrix_R.csv

## 4. Make an order-level scaffold.

DR on the full fish dataset is very messy and does not result in nice
clustering. One of the primary reasons for this is that a given order with two
very old families has a very deep divergent time, and this results in very Long
Branch lengths. This winds up with two clusters that are closely related but
wind up being very far apart when mapped onto the sphere of fish points.

To circumvent this, we First create an order level tree and project these points
onto the sphere. We then do 2D dimensionality reduction on an order by order
basis, and then graft these results back onto the order level points projected
onto the sphere as our scaffold.

`130 Fish species tree scaffold.ipynb`

1. Load in the distance matrix, tree, and taxonomy info.
2. For each order, pick a random species.
3. Make a distance matrix from these random taxa by picking values from the
   loaded-in distance matrix.
4. Run cMDS on this to generate an XYZ point for each order, and use
   `integrate_tree_to_XYZ` to make some branches.

   - `output/random_taxa_mds_coords.csv`
   - `output/random_taxa_mds.branches.csv`
   - `output/random_taxa_mds.internal.csv`
   - `output/random_taxa_mds.leaves.csv`

5. Normalize the points so they are all on the surface of a sphere with radius
   1.0. Run `integrate_tree_to_XYZ` to make proper branches for these too. 

   - `output/random_taxa_mds_coords_norm_on_sphere.csv`
   - `output/random_taxa_mds_coords_norm_on_sphere.branches.csv`
   - `output/random_taxa_mds_coords_norm_on_sphere.internal.csv`
   - `output/random_taxa_mds_coords_norm_on_sphere.leaves.csv`

6. (Suggested by Wandrille and Takanori). Run a relaxation step here to spread
   out the order-level points. The current setup results in some overlap of
   points; this is an attempt to spread out the order-level points to minimize
   these overlaps.

## 5. Run DR on each level separately.

 - `141 Actinopterygii order-level MDS.ipynb`
 - `143 Actinopterygii order-level t-SNE.ipynb`
 - `145 Actinopterygii order-level UMAP.ipynb`

For each order, run 2D DR (MDS, t-SNE, and UMAP) on all the species.

 - `output/mds_by_order/Acanthuriformes_2D_mMDS_sklearn.csv`, etc
 - `output/tsne_by_order/Acipenseriformes_2D_tSNE_sklearn.csv`, etc
 - `output/umap_by_order/Acanthuriformes_2D_UMAP.csv`, etc
 
This notebook also checks for overlapping points. UMAP appears to have the least
incidence of overlapping species-level points.

## 6. Graft 2D order-level points back onto scaffold sphere

Now that we have points spread out for each order, graft those back onto the
scaffold sphere created above. 

 - `151 Graft 2D MDS points onto scaffold sphere.ipynb`
 - `153 Graft 2D tSNE points onto scaffold sphere.ipynb`
 - `155 Graft 2D UMAP points onto scaffold sphere.ipynb`

### Spherical relaxation
 At this point (no pun intended), the points are clumped around each of the
 order points, which doesn't look great. Run Wandrille's
 `spherical-scatterplot-relaxation` script to spread the points further out from
 each other. This notebook uses this script to dump 20 or so runs to an output
 file and load them into a viewer with a slider to pick the most aesthetically
 pleasing result.

 