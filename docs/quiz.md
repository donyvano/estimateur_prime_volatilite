# Quiz d'auto-révision

Pour chaque étape : 2 questions de vocabulaire, 1 de calcul, 1 « explique-le à un recruteur de CACIB », 1 de révision d'une étape précédente.
Réponds **à voix haute ou par écrit avant** d'ouvrir la réponse. Note-toi sur 5, puis reporte le score dans [LEARNING_LOG.md](../LEARNING_LOG.md).

---

## Étape 0 : les bases des options

1. **Vocabulaire.** Définis une option en une phrase avec : droit, obligation, sous-jacent, strike, maturité, prime.
   <details><summary>Réponse</summary>Un contrat qui donne à son acheteur le droit, mais pas l'obligation, d'acheter (call) ou de vendre (put) un sous-jacent à un prix fixé, le strike, à une date donnée, la maturité, en échange d'une prime payée au vendeur.</details>
2. **Vocabulaire.** Quelle est la différence entre « call/put » et « long/short » ?
   <details><summary>Réponse</summary>Call/put = le droit contenu dans le contrat (acheter/vendre le sous-jacent). Long/short = le sens de la position : l'acheteur (long) paie la prime, le vendeur (short) l'encaisse et doit honorer l'option. 4 combinaisons possibles.</details>
3. **Calcul.** Put $K = 480$, prime 6 $, 1 contrat = 100 actions. P&L si $S_T = 450$ ? Si $S_T = 500$ ?
   <details><summary>Réponse</summary>450 : payoff = 480 − 450 = 30 ; P&L = (30 − 6) × 100 = +2 400 $. 500 : payoff 0 ; P&L = −6 × 100 = −600 $ (la prime).</details>
4. **Recruteur.** Pourquoi un vendeur de puts ressemble-t-il à un assureur ?
   <details><summary>Réponse</summary>Il encaisse une prime régulière contre l'engagement de payer en cas de « sinistre » (une forte baisse). Il gagne la plupart du temps, mais une catastrophe peut coûter bien plus que les primes accumulées.</details>
5. **Calcul.** Un call $K = 100$, $S = 105$, prix 8 $. Valeur intrinsèque ? Valeur temps ?
   <details><summary>Réponse</summary>Intrinsèque = 105 − 100 = 5 $. Valeur temps = 8 − 5 = 3 $.</details>

## Étape 1 : données

1. **Vocabulaire.** Rendement simple vs log-rendement : formules, et pourquoi préférer le log ?
   <details><summary>Réponse</summary>$R = P_t/P_{t-1} - 1$, $r = \ln(P_t/P_{t-1})$. Les log-rendements s'additionnent dans le temps et sont symétriques, ce qui simplifie les fenêtres glissantes et les modèles. Quasi égaux pour de petits mouvements.</details>
2. **Vocabulaire.** Pourquoi 252 ?
   <details><summary>Réponse</summary>C'est le nombre approximatif de séances de bourse par an (365 − week-ends − jours fériés). C'est le facteur d'annualisation.</details>
3. **Calcul.** Le prix passe de 200 à 190. Rendement simple ? Log-rendement ?
   <details><summary>Réponse</summary>Simple : −5 %. Log : ln(0,95) ≈ −5,13 %.</details>
4. **Recruteur.** Quels contrôles fais-tu sur les données et pourquoi ?
   <details><summary>Réponse</summary>Dates croissantes sans doublon, prix strictement positifs, clôture entre le plus bas et le plus haut, pas de trou de plus de 5 jours (le plus long légitime : l'ouragan Sandy). Un seul prix faux fait exploser une volatilité ou un backtest sans aucun message d'erreur. Les taux, eux, peuvent légitimement être nuls.</details>
5. **Révision étape 0.** Que signifie $S_T$ ?
   <details><summary>Réponse</summary>Le prix du sous-jacent à la date de maturité $T$.</details>

## Étape 2 : volatilité réalisée

1. **Vocabulaire.** Définis la volatilité réalisée en une phrase.
   <details><summary>Réponse</summary>L'écart-type des rendements observés sur une fenêtre passée, annualisé : l'agitation qui a effectivement eu lieu.</details>
2. **Vocabulaire.** Qu'est-ce que le clustering de volatilité ?
   <details><summary>Réponse</summary>Les périodes agitées se suivent et les périodes calmes aussi : la volatilité est persistante (autocorrélation 0,66 à un mois dans le projet), donc en partie prévisible.</details>
3. **Calcul.** Si le VIX vaut 20, quelle variation journalière typique le marché anticipe-t-il ?
   <details><summary>Réponse</summary>20 % / √252 ≈ 20 / 15,87 ≈ 1,26 % par jour.</details>
4. **Recruteur.** Pourquoi ne retires-tu pas la moyenne dans ta volatilité réalisée ?
   <details><summary>Réponse</summary>C'est la convention des variance swaps, et le VIX est un taux de variance swap : on compare des choses comparables. De plus, la moyenne journalière (~0,03 %) est négligeable et très bruitée sur 21 jours.</details>
5. **Révision étape 1.** Pourquoi Parkinson donne-t-il une vol plus basse que close-to-close ?
   <details><summary>Réponse</summary>Il n'utilise que le plus haut et le plus bas intraday, donc il ignore les gaps entre la clôture de la veille et l'ouverture (environ 0,82× dans le projet).</details>

## Étape 3 : Black-Scholes et Monte Carlo

1. **Vocabulaire.** Cite 4 hypothèses de Black-Scholes.
   <details><summary>Réponse</summary>Prix en mouvement brownien géométrique (log-normal), volatilité constante, taux constant, pas de coûts de transaction ni d'arbitrage, échange en continu.</details>
2. **Vocabulaire.** Explique delta, gamma, vega et theta en une phrase « trader » chacun.
   <details><summary>Réponse</summary>Delta : combien je gagne si le sous-jacent monte de 1 $. Gamma : à quelle vitesse mon delta change. Vega : combien je gagne si la vol implicite monte d'un point. Theta : combien je perds par jour qui passe.</details>
3. **Calcul.** Un Monte Carlo à 10 000 trajectoires a une erreur standard de 0,20 $. Combien de trajectoires pour 0,05 $ ?
   <details><summary>Réponse</summary>Erreur ∝ 1/√N : diviser l'erreur par 4 demande 16× plus de trajectoires, soit 160 000.</details>
4. **Recruteur.** Comment as-tu vérifié tes grecques ?
   <details><summary>Réponse</summary>Contre des différences finies centrées sur le prix Black-Scholes (par exemple delta ≈ [P(S+h) − P(S−h)] / 2h), plus des tests de signe, la parité call-put à $10^{-10}$ et les valeurs de référence du Hull.</details>
5. **Révision étape 2.** Pourquoi la volatilité croît-elle en racine du temps ?
   <details><summary>Réponse</summary>Avec des rendements indépendants, les variances s'additionnent : la variance sur n jours = n × variance journalière, donc l'écart-type = √n × écart-type journalier.</details>

## Étape 4 : volatilité implicite

1. **Vocabulaire.** Définis la volatilité implicite en une phrase.
   <details><summary>Réponse</summary>La volatilité qui, mise dans Black-Scholes, redonne le prix de marché de l'option : la vol que le marché fait payer, pas une mesure du passé.</details>
2. **Vocabulaire.** Qu'est-ce que le skew et pourquoi existe-t-il sur les actions ?
   <details><summary>Réponse</summary>La vol implicite est plus élevée pour les strikes bas (puts) que pour les strikes hauts. Causes : demande de protection par les investisseurs, krachs plus brutaux que les hausses, effet de levier.</details>
3. **Calcul.** Parité call-put : $C = 12$, $P = 7$, $K = 100$, $e^{-rT} = 0{,}99$. Forward implicite ?
   <details><summary>Réponse</summary>$C - P = e^{-rT}(F - K)$ → $5 = 0{,}99 (F - 100)$ → $F ≈ 105{,}05$.</details>
4. **Recruteur.** Pourquoi Newton puis Brent ?
   <details><summary>Réponse</summary>Newton converge très vite (quadratiquement) près de l'ATM, mais divise par la vega, qui s'écrase pour les options très OTM ou courtes : le pas explose. Brent encadre la racine et converge toujours, car le prix est monotone en σ.</details>
5. **Révision étape 3.** Pourquoi ne garder que les options OTM ?
   <details><summary>Réponse</summary>Elles sont plus liquides, et comme les options SPY sont américaines, les OTM ont une prime d'exercice anticipé quasi nulle : la formule européenne s'applique.</details>

## Étape 5 : la prime de volatilité

1. **Vocabulaire.** Définis la prime de volatilité.
   <details><summary>Réponse</summary>VRP = volatilité implicite (VIX en t) − volatilité réalisée ensuite (de t+1 à t+21). C'est le prix de l'assurance moins les sinistres payés.</details>
2. **Vocabulaire.** Qu'est-ce que le biais de look-ahead ? Donne un exemple dans ce projet.
   <details><summary>Réponse</summary>Utiliser en t une information non connue à la clôture de t. Exemple : la vol réalisée de t+1 à t+21 n'est connue qu'en t+21 : c'est une cible, jamais une variable explicative.</details>
3. **Calcul.** VIX = 25, vol réalisée le mois suivant = 18. VRP en vol ? En variance ($\times 10^4$) ?
   <details><summary>Réponse</summary>Vol : 25 − 18 = +7 points. Variance : 25² − 18² = 625 − 324 = 301 points de variance.</details>
4. **Recruteur.** Quel est ton résultat principal et comment sais-tu qu'il n'y a pas de triche ?
   <details><summary>Réponse</summary>+3,5 points en moyenne (médiane +4,3), positive 84 % du temps sur 2005-2026. Des tests modifient les prix futurs et vérifient que toutes les variables « connues en t » sont inchangées, et que la cible, elle, bouge.</details>
5. **Révision étape 4.** Pourquoi le VIX (19,4 %) est-il au-dessus de la vol ATM 1 mois (15,8 %) ?
   <details><summary>Réponse</summary>Le VIX agrège tous les strikes, y compris les puts OTM chers à cause du skew, alors que la vol ATM ne regarde que le strike au forward.</details>

## Étape 6 : prévision

1. **Vocabulaire.** Qu'est-ce que le modèle HAR-RV ?
   <details><summary>Réponse</summary>Une régression de la variance future sur les variances réalisées à 1 jour, 5 jours et 22 jours : une cascade d'horizons qui capture la persistance de la volatilité.</details>
2. **Vocabulaire.** Pourquoi un split aléatoire triche-t-il sur une série temporelle ?
   <details><summary>Réponse</summary>Il entraîne sur des données postérieures au test. Avec des cibles qui se chevauchent (21 jours) et une volatilité persistante, des jours voisins du test se retrouvent dans l'entraînement : fuite d'information, performance surestimée.</details>
3. **Calcul.** Vol réalisée 20 %, prévision 16 %. QLIKE ? Et si la prévision vaut 25 % ?
   <details><summary>Réponse</summary>Ratio des variances 0,04/0,0256 = 1,5625 → QLIKE = 1,5625 − ln(1,5625) − 1 ≈ 0,116. Avec 25 % : 0,04/0,0625 = 0,64 → 0,64 − ln(0,64) − 1 ≈ 0,086. La sous-estimation coûte plus cher.</details>
4. **Recruteur.** Pourquoi ton LightGBM ne bat-il pas un modèle linéaire ?
   <details><summary>Réponse</summary>Le signal est dominé par une structure simple, persistance plus VIX, que le linéaire capte déjà, et les arbres extrapolent mal lors des chocs rares. LightGBM a la meilleure MAE, mais il sous-estime les pics, ce que QLIKE sanctionne. Sa variable la plus importante est d'ailleurs le VIX.</details>
5. **Révision étape 5.** Qu'est-ce que la purge de 21 jours ?
   <details><summary>Réponse</summary>On retire de l'entraînement les 21 dernières dates avant l'année de test, car leur cible (vol de t+1 à t+21) déborde sur la période de test.</details>

## Étape 7 : backtest

1. **Vocabulaire.** Qu'est-ce qu'un variance swap ?
   <details><summary>Réponse</summary>Un contrat qui échange la variance réalisée contre un strike de variance fixé au départ. Le vendeur encaisse K² et paie la variance réalisée : il est short volatilité.</details>
2. **Vocabulaire.** Pourquoi un Sharpe élevé peut-il cacher un risque de krach ?
   <details><summary>Réponse</summary>Le Sharpe ne regarde que la moyenne et l'écart-type. Une stratégie à skew très négatif (beaucoup de petits gains, de rares pertes énormes) peut avoir un bon Sharpe tant que le krach n'est pas dans l'échantillon. Il faut aussi regarder le drawdown, le skew, la kurtosis et la CVaR.</details>
3. **Calcul.** Variance swap vendu à K = 20. P&L par unité de vega si RV = 15 ? Si RV = 40 ?
   <details><summary>Réponse</summary>(K² − RV²)/(2K) : (400 − 225)/40 = +4,375 pts ; (400 − 1 600)/40 = −30 pts. Les pertes sont convexes.</details>
4. **Recruteur.** Que conclus-tu de ton backtest ?
   <details><summary>Réponse</summary>La prime existe, mais la vendre, c'est porter un risque de queue (skew −4,5, pire mois −32 %). Filtrer par la prévision réduit surtout le drawdown (−46 % → −19 %). Le Sharpe dépend énormément de la date de roll (0,36 à 1,71), donc je ne survends pas le résultat.</details>
5. **Révision étape 6.** Pourquoi avoir fixé le seuil à 2 points a priori ?
   <details><summary>Réponse</summary>Pour éviter le data snooping : optimiser le seuil sur la période testée gonflerait artificiellement la performance. La sensibilité au seuil est affichée, pas exploitée.</details>

---

## Test final (15 questions)

1. Quelle est la différence entre volatilité implicite et volatilité réalisée ?
2. Le VIX vaut 30. Quel mouvement journalier typique le marché anticipe-t-il ?
3. Donne la formule de la volatilité réalisée utilisée dans le projet.
4. Écris la parité call-put avec dividendes.
5. Le gamma d'un vendeur d'options est-il positif ou négatif ? Qu'est-ce que ça implique ?
6. Pourquoi l'erreur d'un Monte Carlo décroît-elle en $1/\sqrt{N}$ ?
7. Pourquoi Newton-Raphson peut-il échouer dans l'inversion de la vol implicite ?
8. Qu'est-ce qu'une structure par terme inversée et quand l'observe-t-on ?
9. Quelle est la VRP moyenne du projet, et quel pourcentage du temps est-elle positive ?
10. Comment as-tu testé l'absence de look-ahead ?
11. Pourquoi QLIKE plutôt que RMSE seule ?
12. Quel modèle de prévision gagne, et de combien par rapport au naïf ?
13. Pourquoi le P&L d'un variance swap est-il convexe en la volatilité réalisée ?
14. Pourquoi la sensibilité à la date de roll est-elle importante ?
15. Cite trois limites du projet et comment tu les lèverais.

<details><summary>Réponses du test final</summary>

1. L'implicite est anticipée, lue dans les prix d'options (forward-looking). La réalisée est mesurée sur les rendements passés.
2. 30 / √252 ≈ 1,9 % par jour.
3. $\sigma_t = \sqrt{\frac{252}{21}\sum_{i=t-20}^{t} r_i^2}$, avec des log-rendements non centrés.
4. $C - P = S e^{-qT} - K e^{-rT}$.
5. Négatif : il perd sur les gros mouvements dans un sens comme dans l'autre, et doit racheter haut et revendre bas pour rester couvert.
6. TCL : l'écart-type de la moyenne empirique vaut $\sigma/\sqrt{N}$.
7. Il divise par la vega, qui est quasi nulle pour les options très OTM ou courtes : le pas explose ou sort des bornes. D'où le repli sur Brent.
8. Une vol courte plus élevée que la vol longue : en crise, le stress immédiat domine (mars 2020 par exemple).
9. +3,5 points en moyenne (médiane +4,3), positive 84 % des jours.
10. On modifie les prix après t et on vérifie que toutes les variables « connues en t » restent identiques jusqu'à t, que la cible bouge, et que la dernière cible d'entraînement se termine avant la période de test.
11. QLIKE est robuste au bruit du proxy de variance et pénalise davantage la sous-estimation du risque, ce qui compte pour un risk manager.
12. HAR-RV + VIX : RMSE −13,8 % par rapport au naïf.
13. Le payoff porte sur la variance ($RV^2$) : une vol qui double fait quadrupler la variance, donc les pertes du vendeur s'accélèrent.
14. Avec des trades mensuels, un krach juste après un roll pèse lourd : sur une seule date de roll, le Sharpe peut être un coup de chance (0,36 à 1,71 selon la date).
15. Pas d'historique d'options (→ OptionMetrics), VIX non négociable (→ backtest sur straddles couverts en delta), snapshot du smile issu des derniers prix (→ snapshot pendant les heures de marché), pas de test statistique (→ Diebold-Mariano, bootstrap du Sharpe).
</details>

---

## Simulation d'entretien : 10 questions d'un data scientist de CACIB

Entraîne-toi à répondre en 1 minute chacune. Les éléments attendus sont dans les réponses.

1. « Votre VIX est un indice sur SPX, mais votre smile est sur SPY. Est-ce cohérent ? »
   <details><summary>Éléments attendus</summary>SPY réplique le S&P 500 à 1/10 près, avec des dividendes et un exercice américain. Je ne compare pas directement les niveaux : le smile SPY sert à illustrer le skew, et la VRP historique est entièrement sur VIX/SPX. Avec plus de données, je prendrais le smile SPX (européen).</details>
2. « Pourquoi 21 jours de bourse pour un VIX à 30 jours calendaires ? »
   <details><summary>Éléments attendus</summary>30 jours calendaires ≈ 21-22 séances. C'est une approximation standard, documentée ; un jour de différence change très peu la moyenne de la prime.</details>
3. « Votre HAR bat LightGBM. Avez-vous bien tuné LightGBM ? »
   <details><summary>Éléments attendus</summary>Les hyperparamètres sont fixés a priori, volontairement : les tuner sur la période de test serait du snooping. La bonne réponse serait un tuning en validation imbriquée (walk-forward interne). Le résultat est cohérent avec la littérature, où les modèles HAR sont très durs à battre.</details>
4. « Comment savez-vous que l'écart de RMSE est significatif ? »
   <details><summary>Éléments attendus</summary>Je ne le sais pas encore formellement : il faudrait un test de Diebold-Mariano avec erreurs HAC, puisque les erreurs sur cibles chevauchantes sont autocorrélées. C'est dans les pistes.</details>
5. « Votre stratégie aurait-elle survécu à 2008 ? »
   <details><summary>Éléments attendus</summary>Le backtest commence en 2010 (il faut des données d'entraînement). Sur la crise de 2008, la prime moyenne est de −3,8 points et la pire de −50 : vendre systématiquement aurait été très douloureux. Avec 0,5 % du capital par point de vol et un cap à 2,5×, la perte reste bornée, mais le sizing est crucial.</details>
6. « Pourquoi plafonner la variance réalisée ? »
   <details><summary>Éléments attendus</summary>C'est la pratique de marché sur les variance swaps d'indices depuis 2008 (cap à 2,5× le strike) : le vendeur limite sa perte maximale. Exemple du projet : swap vendu le 7 février 2020 à 15,5, vol réalisée 47,9 % → perte de 40,6 points avec cap, 66,3 sans.</details>
7. « Le VIX n'est pas négociable. Que vaut votre backtest ? »
   <details><summary>Éléments attendus</summary>C'est un proxy : le VIX² approxime le strike d'un variance swap 30 jours, mais les strikes réels sont un peu plus hauts (convexité, bid-ask), ce qui réduirait la performance. Les coûts de 0,5 point en absorbent une partie. Un vrai backtest utiliserait des prix de swaps ou des straddles couverts en delta.</details>
8. « Expliquez la différence entre theta et la prime de volatilité. »
   <details><summary>Éléments attendus</summary>Le theta est l'érosion mécanique du prix d'une option avec le temps. Pour une position couverte en delta, le P&L ≈ ½ Γ S² (σ²_réalisée − σ²_implicite) dt : le vendeur gagne le theta et paie le gamma, et le solde moyen de ce combat, c'est la prime de volatilité.</details>
9. « Comment mettriez-vous ce modèle en production ? »
   <details><summary>Éléments attendus</summary>Pipeline quotidien après la clôture (le code est déjà un package avec CI), données d'un fournisseur fiable, monitoring de la dérive des erreurs de prévision, ré-entraînement annuel comme dans le walk-forward, alertes sur la qualité des données (les contrôles existent déjà).</details>
10. « Qu'avez-vous appris de plus surprenant ? »
   <details><summary>Éléments attendus</summary>Que la prime est positive même quand le VIX est très haut (84 % du temps quel que soit le régime), et qu'un détail comme la date de roll peut faire varier un Sharpe du simple au quadruple. Un backtest doit montrer sa distribution de résultats, pas son meilleur chemin.</details>
