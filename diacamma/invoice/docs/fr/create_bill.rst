Création de facture
===================

Création
--------

Depuis le menu *Facturier/Facture* vous pouvez éditer ou ajouter une nouvelle facture.

Commencez par définir le type de document (devis, facture, reçu ou avoir) que vous souhaitez créer ainsi que la date d'émission et un commentaire qui figurera dessus.

Dans cette facture, vous devez préciser le client associé, c'est à dire le tiers comptable imputable de l'opération.

    .. image:: bill_edit.png

Ensuite ajoutez ou enlevez autant d'articles que vous le désirez.

    .. image:: add_article.png

Par défaut, vous obtenez la désignation et le prix par défaut de l'article sélectionné, mais l'ensemble est modifiable. Vous pouvez choisir aussi l'article divers: aucune information par défaut n'est alors proposé.

Si l'article a été défini comme *stockable*, vous devrez en plus préciser depuis quel lieu de stockage il sera sortie.
Il n'est bien sur pas possible de vendre plus d'article stockable que l'on possède dans le stock.  

Création en lot
---------------

Depuis le menu *Facturier/Facture*, vous pouvez créer des factures en lot via le bouton "En lot".

Pour cela, vous devez définir un "critère sauvegarder" de recherche de tiers (à réaliser via le menu "Comptabilité > Tiers" - bouton "Recherche").  
Précisez également le type de document (devis, facture, avoir ou reçu) à réaliser ainsi que l'article à inclure (un seul possible).

Valider la création: la génération des justificatifs, liés aux tiers définis dans la recherche, sera alors réalisée.   
Ces justificatifs seront à l'état "en création": vous pouvez donc les controler avant de les valider et les envoyer.

Changement d'état
-----------------

Depuis le menu *Facturier/Facture* vous pouvez consulter les factures en cours, validé ou fini.

Un devis, une facture, un reçu ou un avoir dans l'état « en cours » est un document en cours de conception et il n'est pas encore envoyé au client.

Depuis la fiche du document, vous pouvez le valider: il devient alors imprimable et non modifiable.

Dans ces deux cas, une écriture comptable est alors automatiquement générée.

Un devis validé peut facilement être transformé en facture dans le cas de son acceptation par votre client. La facture ainsi créé se retrouve alors dans l'état « en cours » pour vous permettre de la réajuster.

Une fois qu'une facture (ou un avoir) est considéré comme terminée (c'est à dire réglée ou définie comme pertes et profits), vous pouvez définir son état à «fini».

Depuis une facture « fini », il vous est possible de créer un avoir correspondant à l'état « en cours ». Cette fonctionnalité vous sera utile si vous êtes amené à rembourser un client d'un bien ou un service précédemment facturé.

Si une facture contiens des articles *stockable*, un bordereau de sortie est automatiquement générer pour correspondre à cette vente.
La situation du stock est alors mise à jour automatiquement.

Impression
----------

Depuis la fiche d'un document (devis, facture, reçu ou avoir) vous pouvez à tout moment imprimer ou réimprimer celui-ci s'il n'est pas à l'état «en cours».

Pour les factures, les reçus ou les avoirs, une sauvegarde officielle (d'après le modèle d'impression par défaut) est automatiquement sauvegardée dans le gestionnaire de documents au moment de la validation.
Lorsque vous voulez imprimer le justificatif, on vous propose alors par défaut de télécharger ce document sauvegardé.
Vous pouvez régénérer un nouveau PDF, par exemple avec un autre modèle d'impression. Par contre celui-ci comportera la mention "duplicata" en filigrane.

Paiement
--------

Si ceux-ci sont configurés (menu *Administration/Modules (conf.)/Configuration du règlement*), vous pouvez consulter les moyens de paiement d'une facture, d'un reçu ou d'un devis.
Si vous l'envoyez par courriel, vous pouvez également les faire apparaitre dans votre message.

Dans le cas d'un paiement via PayPal, si votre _Diacamma_ est accessible par internet, le logiciel sera automatiquement notifié du règlement.
Dans le cas d'un devis, celui-ci sera automatiquement archivé et une facture équivalente sera générée.
Un nouveau réglement sera ajouté dans votre facture.

Dans l'écran *Comptabilité/Transactions bancaires*, vous pouvez consulté précisement la notification reçu de PayPal.
En cas d'état "échec", la raison est alors précisé: il vous faudra manuellement vérifier votre compte PayPal et rétablir l'éventuellement paiment erroné manuellement.

 
 