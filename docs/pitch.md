# Pitch d'entretien : 30 secondes par étape

Format : ce que j'ai fait → pourquoi c'est important → un chiffre ou un détail technique qui montre que je maîtrise.
Lis-les à voix haute, chronomètre-toi (≈ 80 mots = 30 secondes), puis reformule avec tes mots.

---

## Pitch global (1 minute)

« J'ai mesuré la prime de volatilité du S&P 500 : l'écart entre la volatilité que le marché anticipe, le VIX, et celle qui se réalise ensuite. Sur 2005-2026, le VIX surestime la volatilité du mois suivant de 3,5 points en moyenne, 84 % du temps. C'est le prix de l'assurance contre les krachs. J'ai ensuite comparé cinq modèles de prévision en walk-forward : un HAR-RV qui intègre le VIX bat le naïf de 14 %, et bat aussi LightGBM. Enfin, j'ai backtesté la vente d'un variance swap : filtrer par la prévision divise le drawdown par plus de deux, mais j'ai montré que le Sharpe dépend énormément de la date de roll. Tout est testé, sans look-ahead, et restitué sur un site web. »

---

## Étape 0 : cadrage
« J'ai structuré le projet comme du code de production : une config YAML unique pour tous les paramètres, un package Python testé, et une CI GitHub qui lance le lint et 115 tests à chaque push. En banque, un modèle doit être reproductible : si un risk manager relance mon calcul dans six mois, il doit retrouver le même chiffre. Les seeds sont fixées et les données sont mises en cache en parquet. »

## Étape 1 : données
« Je télécharge 21 ans de S&P 500, de VIX et de taux T-bill, plus une chaîne d'options SPY. Chaque série passe des contrôles automatiques : prix positifs, dates croissantes, clôture entre le plus bas et le plus haut, pas de trou de plus de 5 jours. J'ai découvert qu'il ne faut pas appliquer le filtre "prix positif" aux taux : les T-bills étaient à 0 % en 2020. Petit détail, mais c'est le genre de bug silencieux qui fausse tout. »

## Étape 2 : volatilité réalisée
« J'ai calculé la volatilité réalisée sur 21 jours glissants, annualisée par racine de 252, sans retirer la moyenne : c'est la convention des variance swaps, donc du VIX. Je l'ai comparée à l'estimateur de Parkinson, qui utilise les plus hauts et plus bas : il ressort 18 % plus bas, car il ignore les gaps de nuit. La volatilité est très persistante, avec une autocorrélation de 0,66 à un mois : c'est ce qui la rend prévisible. »

## Étape 3 : Black-Scholes et Monte Carlo
« J'ai codé Black-Scholes et les quatre grecques, en vectorisé, et je les teste contre des différences finies : le delta, le gamma, la vega et le theta analytiques doivent coller à la dérivée numérique. J'ai aussi un pricer Monte Carlo sur la loi exacte du brownien géométrique : l'erreur décroît en un sur racine de N, 3,8 $ à 100 trajectoires, 0,002 $ à 300 000. C'est exactement le théorème central limite de mon cours de Monte Carlo à l'EFREI. »

## Étape 4 : volatilité implicite
« J'inverse Black-Scholes par Newton-Raphson sur la vega, avec un repli sur Brent quand la vega s'écrase, sur les options très hors de la monnaie. Plutôt que de deviner les dividendes, je déduis le forward de chaque échéance par la parité call-put. Je ne garde que les options hors de la monnaie et liquides. Résultat : un skew de 15 points entre le put à 90 % et le call à 110 %. Le marché paie cher la protection contre les krachs. »

## Étape 5 : la prime de volatilité
« J'aligne le VIX du jour t avec la volatilité réalisée de t+1 à t+21, et je le teste explicitement : si je modifie les prix futurs, aucune variable connue en t ne doit bouger. La prime moyenne est de 3,5 points, positive 84 % du temps, quel que soit le niveau du VIX. Mais elle s'effondre en crise : −72 points la veille du krach Covid. C'est exactement le profil d'un assureur. »

## Étape 6 : prévision
« J'ai comparé cinq modèles en walk-forward annuel, avec une purge de 21 jours pour que la cible d'entraînement ne déborde jamais sur la période de test. Un split aléatoire tricherait à cause de la persistance de la volatilité. Le gagnant est un HAR-RV augmenté du VIX, −14 % d'erreur. LightGBM a la meilleure erreur absolue mais sous-estime les chocs, ce que la perte QLIKE sanctionne. Sa variable la plus importante, c'est le VIX lui-même. »

## Étape 7 : backtest
« Je vends chaque mois un variance swap au niveau du VIX, avec un plafond à 2,5 fois le strike et des coûts. Vendre systématiquement donne un Sharpe de 0,76, mais un drawdown de −46 % et un skew de −4,5. Ne vendre que si la prime prévue dépasse 2 points ramène le drawdown à −19 %. Surtout, j'ai testé les 21 dates de roll possibles : le Sharpe va de 0,36 à 1,71. Un backtest sur un seul chemin aurait raconté une histoire trop belle. »

## Étape 8 : restitution
« Python calcule tout et exporte des JSON. Un site statique, déployé automatiquement sur GitHub Pages, raconte le projet en six sections avec des graphiques interactifs. Le rapport de méthodologie documente chaque filtre, chaque approximation et chaque limite, notamment l'absence d'historique d'options gratuit. Mon objectif : qu'un desk puisse auditer chaque chiffre. »
