Configuration et paramétrage
============================

Catégories
----------

Le menu *Administration/Modules (conf.)/Configuration commercial du facturier*, onglet *Catégorie*

Vous pouvez définir des catégories afin de classer vos articles.
Chaque article peut être associé à plusieurs catégories.

Champ personnalisé
------------------

Le menu *Administration/Modules (conf.)/Configuration commercial du facturier*, onglet *Champ personnalisé*

Comme pour les contacts, vous pouvez ici définir des champs personnalisés.

Lieu de stockage
----------------

Le menu *Administration/Modules (conf.)/Configuration commercial du facturier*, onglet *Lieu de stockage*

Si vous voulez gérer une centrale d'achat, vous pouvez ici définir les différents espace de vos articles stockables.

Réduction automatique
---------------------

Le menu *Administration/Modules (conf.)/Configuration commercial du facturier*, onglet *Réduction automatique*

Ce tableau de gestion de réductions comporte les champs suivants:
 - La catégorie d'article impacté.
 - Le type de réduction: en valeur, en pourcentage, en pourcentage global déjà vendu.
 - Le montant de la réduction (en valeur ou pourcentage suivant le type).
 - Le nombre d'occurrence déclenchant la réduction.
 - Un critère de filtrage du tiers à qui cette réduction s'applique. (Optionnel)

Au moment d'ajout d'un article dans une facture, si le client de cette facture et ce nouvel article répond à aux critères d'une réduction,
celle-ci s'applique alors automatiquement dans la facture.
Si plusieurs réductions remplissent leurs conditions, c'est la réduction octroyant la plus grande réduction qui sera utilisé.
Un article peut se retrouver vendu gratuitement, mais jamais négativement (qui reviendrait à un remboursement)
Ce mécanisme sera également appliqué lors de la création automatique des factures (cotisation, participation à un événement)
Ce mécanisme vérifie le critère que pour des opérations réalisés sur l'exercice financier courant de l'association (les réductions ne se cumule pas d'une année à l'autre)

Catégorie de facturation
------------------------

Le menu *Administration/Modules (conf.)/Configuration commercial du facturier*, onglet *Catégorie de facturation*

Vous pouvez définir des catégories de facturation afin de modifier le nom du type de vos justificatif ou personnaliser vos patrons d'impression.
Il vous est également possible de préciser que les devis/factures de cette catégorie auront une numérotation propre (avec un éventuelle préfixe de spécification.
Les moyens de paiement proposés ainsi que le message par défaut lors de l'envoie par courriel peuvent également être personnalisé.

Notez que si vous définissez des catégories de facturation, la liste des facture (menu *Facturier/Facture*) vous proposera un filtrage par type spécifique de chaque catégorie.

Gestion de panier
-----------------

Le menu *Administration/Modules (conf.)/Configuration commercial du facturier*, onglet *Panier*

Vous pouvez ici activer la fonctionnalité d'achat par panier.
Un nouveau menu *General/Panier d'achat* apparait alors à tout les utilisateurs ayant le droit spécifique "[Facturier Diacamma] facture : panier".

D'autres paramètres permet d'affiner l'a fonctionnalité
 - Filtre d'article pour le panier : défini un critère de recherche sauvegardé des articles vendables par panier.
 - Temps de vie d'un panier (jours : défini le temps de conversation (en jours) d'un panier non validé. laissez "0" si vous ne voulez pas les nettoyer automatiquement.
 - sujet et message pour courriel de panier : permet de personnaliser le courriel envoyé à l'acheteur une fois le panier validé.
 
Codes d'imputations comptable
-----------------------------

Menu *Administration/Modules (conf.)/Configuration financière du facturier*, onglet *Codes d'imputations comptable*

Un "Code d'imputation comptable" contiens:
 - un code comptable de vente
 - un code analytique (optionnel) 

Chaque article peut être associé à un code d'imputation comptable (si non précisé, l'article n'est pas vendable).
Ce mécanisme permet de centraliser à un seul endroit les configurations comptables des articles.
Au changement d'exercice, si ces configurations doivent changées, il est plus simple de modifier cette configuration que l'ensemble des articles.

Un champs spécifique peut également être demandé si la gestion des *comande* est autorisée: "compte de tiers de provision". 
Ce compte de tiers sera utilisé par la commande (plutôt que le code comptable habituel "client") dans le cas où l'on sait que les futures commandes seront transformé en facture dans un laps de temps long (ex: approvisionnement d'article).

Codes comptables par défaut
---------------------------

Menu *Administration/Modules (conf.)/Configuration financière du facturier*, onglet *Paramètres*

Ce module est intimement lié au module de gestion comptable, un certain nombre de codes comptables par défaut sont nécessaires.

Pour pouvoir générer les écritures comptables correspondants aux factures saisies avec des articles non référencés, vous devez préciser le code comptable de vente (classe 7) lié a ce type de d'article. Par défaut, le code comptable de vente de service est défini.

Pour réaliser une réduction sur un article, vous devez préciser le code comptable de vente à imputer de cette réduction.
Dans le cas de règlement en liquide, il vous faut préciser le code comptable de banque associé à votre caisse.

La configuration de la TVA
--------------------------

Menu *Administration/Modules (conf.)/Configuration financière du facturier*, onglet *TVA*

Vous pouvez complètement configurer la gestion de votre soumission à la TVA.

.. image:: vat.png

Pour commencer, vous devez définir les modalités de soumission en sélectionnant votre mode d'application:

 - TVA non applicable
	Vous n'êtes pas soumis à la TVA. L'ensemble de vos factures sont réalisées hors-taxe.
 - Prix HT
    Vous êtes soumis à la TVA. Vous faites le choix d'éditer vos factures avec les montants des articles en hors-taxe.
 - Prix TTC
    Vous êtes soumis à la TVA. Vous faites le choix d'éditer vos factures avec les montants des articles toutes taxes comprises. 

Précisez également le compte comptable d'imputation de ces taxes.

Définissez l'ensemble des taux de taxes auxquels vos ventes sont soumises. La taxe par défaut sera celle appliquée à l'article libre (sans référence).
