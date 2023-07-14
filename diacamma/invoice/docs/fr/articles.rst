Les articles
============

Création et modification
------------------------

Depuis le menu *Facturier/Les articles* vous avez la possibilité de définir l'ensemble de vos articles facturables.

.. image:: articles_list.png

Vous pouvez ajouter, modifier ou supprimer un article. La suppression n'est pas possible si l'article est utilisé dans une facture.

A chaque article, vous devez définir un code comptable d'imputation pour la génération d'écritures automatique.

Le champ *stockable* permet de définir si vous voulez gérer une gestion de stock de cet article:
 * non stockable
    Article sans gestion de stock, comme par exemple des articles de service.
 * stockable
    Article stockable et facturable.
 * stockable & non vendable
    Article stockable non proposable à la vente.
    Utile pour suivre des stocks de matériel interne.

De plus, dans le cas où vous réalisez des factures avec TVA, vous devrez préciser, pour chaque articles, le taux de taxe à appliquer.

L'onglet *Fournisseur* permet d'identifier des références fournisseurs pour simplifier leur commande ou leur référencement.

Le champ *code d'imputation comptable* permet d'associer à cet article une configuration comptable (voir *Configuration et paramétrage*)

La facture avec TVA
-------------------

Si vous êtes soumis à la TVA, l'édition de la facture change un peu

En plus de préciser si les articles sont en montant HT ou TTC, vous avez en bas de l'écran le total de la facture hors-taxe, taxes comprises ainsi que le montant total des taxes.

De plus, dans l'impression de la facture, un sous-détail des taxes apparait par taux de TVA.

Import d'articles
-----------------

Depuis le menu *Administration/Modules (conf.)/Import d'article*, vous avez la possibilité d'importer des articles en lot depuis un fichier CSV, ODS ou XLS.

Une fois avoir sélectionné votre fichier et les information de son format,
vous serez ammené à associer les champs d'un article aux colonnes de votre documents (la première ligne de votre document doit décrire la nature de chaque colonne).
    
Vous pouvez alors contrôler vos données avant de les validés.
