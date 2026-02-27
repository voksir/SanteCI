## Sante CI

Application web frontend pour la plateforme Sante CI, construite avec React, TypeScript et Vite.  
Le dépôt contient uniquement la partie **front** (Single Page Application), l’API ou les services métiers vivent en dehors de ce projet.

---

## Stack technique

- **Vite** (bundler / dev server)
- **React 18** + **TypeScript**
- **React Router DOM** (navigation SPA)
- **Tailwind CSS** + **@tailwindcss/typography**
- **shadcn-ui / Radix UI** (bibliothèque de composants `src/components/ui`)
- **React Hook Form** + **Zod** (gestion de formulaires et validation)
- **@tanstack/react-query** (gestion de requêtes et cache côté client, prêt pour des appels API)
- **Vitest** + **Testing Library** (tests unitaires)
- **ESLint** (linting)

---

## Prérequis

- **Node.js** LTS (recommandé ≥ 18)
- **npm** (ou un autre gestionnaire comme `pnpm` ou `yarn` si tu adaptes les commandes)

---

## Installation et scripts NPM

Depuis la racine du projet (`Sante-CI`) :

```sh
npm install
```

Scripts principaux définis dans `package.json` :

- `npm run dev` : lance le serveur de développement Vite (par défaut sur `http://localhost:5173` ou le port configuré).
- `npm run build` : build de production.
- `npm run build:dev` : build en mode développement (utile pour tester un bundle non minifié).
- `npm run preview` : prévisualisation locale du build.
- `npm run lint` : exécute ESLint sur le projet.
- `npm test` : lance la suite de tests Vitest en mode run.
- `npm run test:watch` : lance les tests Vitest en mode watch.

---

## Structure du code

Structure simplifiée des dossiers les plus importants :

```text
src/
  main.tsx              # Point d’entrée Vite / React
  App.tsx               # Composition principale de l’application et du routage

  components/
    Header.tsx          # En-tête / navigation globale
    PageShell.tsx       # Gabarit de page (layout commun)
    ui/                 # Composants UI génériques (shadcn-ui, Radix, etc.)
      button.tsx
      input.tsx
      dialog.tsx
      ...               # Autres composants de base réutilisables

  pages/
    HomePage.tsx        # Page d’accueil / vue globale
    ...                 # Pages thématiques (pharmacies de garde, proximité, prix, assurances, actu, dons, etc.)

  lib/
    utils.ts            # Fonctions utilitaires (ex. helper `cn` pour les classes CSS)

  test/
    setup.ts            # Configuration commune des tests (Testing Library, jest-dom, etc.)
    example.test.ts     # Exemple de test Vitest

  index.css / styles/   # Entrée Tailwind / styles globaux

vite.config.ts          # Configuration Vite (alias `@`, port, plugins…)
tailwind.config.ts      # Configuration Tailwind
postcss.config.js       # Configuration PostCSS
eslint.config.js        # Règles ESLint
vitest.config.ts        # Configuration des tests Vitest
```

Les noms exacts de certaines pages peuvent évoluer, mais la logique reste :  
**`src/pages`** pour les vues fonctionnelles / métiers, **`src/components`** pour les blocs réutilisables, **`src/components/ui`** pour le design system.

---

## Architecture applicative

- **Architecture SPA (Single Page Application)** :
  - Une seule application React, montée dans `main.tsx`, gérée par Vite.
  - Le routage se fait côté client via **React Router DOM**.

- **Séparation pages / composants** :
  - Les routes principales du produit (ex. pharmacies, assurances, dons, actualités) sont implémentées comme des **pages** dans `src/pages`.
  - Les composants réutilisables (boutons, inputs, cartes, dialogues, layouts, etc.) vivent dans `src/components` et plus particulièrement dans `src/components/ui` pour le design system.

- **Layout et shell d’application** :
  - `Header.tsx` gère la navigation globale et l’identité visuelle.
  - `PageShell.tsx` (ou équivalent) fournit un **layout commun** (barre de navigation, contenu principal, pied de page…) pour les différentes pages.

- **Styles et thème** :
  - Tailwind est utilisé pour la mise en page et la typographie, combiné avec des composants shadcn-ui/Radix pour les éléments UI avancés.
  - Des utilitaires comme `cn` (dans `src/lib/utils.ts`) facilitent la composition conditionnelle de classes Tailwind.

- **Gestion des données** :
  - Le dépôt est **frontend only** : il ne contient ni schéma de base de données ni backend.
  - `@tanstack/react-query` est présent pour gérer proprement les appels à des APIs externes (cache, synchronisation, états de chargement/erreur, etc.) dès que tu connecteras le frontend à un backend Sante CI.

---

## Qualité, linting et tests

- **Linting** :
  - Configuration centrale : `eslint.config.js`.
  - Commande : `npm run lint`.

- **Tests** :
  - Framework : **Vitest**.
  - Intégration DOM : **@testing-library/react** + **@testing-library/jest-dom**.
  - Configuration : `vitest.config.ts` + `src/test/setup.ts`.
  - Exécution :
    - `npm test` pour une exécution unique de la suite de tests.
    - `npm run test:watch` pour développer en TDD.

---

## Configuration et variables d’environnement

Le projet ne contient pas encore de fichier `.env` versionné, mais il est prévu de consommer des **APIs externes** (backend Sante CI, services tiers, etc.).  
Il est recommandé de :

- Utiliser les variables d’environnement Vite (`import.meta.env.VITE_*`) pour les valeurs **non sensibles** nécessaires au frontend (URLs publiques, clés publiques).
- Ne **jamais** commiter de secrets (tokens privés, mots de passe, clés privées).
- Documenter dans cette section, au fur et à mesure, les variables réellement utilisées (ex. `VITE_API_URL`, `VITE_MAPS_API_KEY`, etc.).

---

## Évolution possible de l’architecture

Quelques pistes naturelles d’évolution de ce codebase :

- Introduire une structure par **domaines métier** dans `src/pages` et `src/components` (ex. `patient/`, `rdv/`, `facturation/`, `assurance/`…).
- Centraliser la logique d’accès aux APIs dans un module dédié (ex. `src/lib/api/` ou `src/services/`) en s’appuyant sur `react-query`.
- Ajouter une couche de **gestion d’état global** si nécessaire (par exemple pour l’authentification, les préférences utilisateur, etc.).

Ce README pourra être complété à mesure que le backend Sante CI, les appels API concrets et les règles métier seront intégrés dans ce dépôt.
