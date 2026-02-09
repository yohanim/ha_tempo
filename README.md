# Home Assistant - Intégration Tempo RTE, Prévisions & Prix

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub release](https://img.shields.io/github/release/yohanim/ha_tempo.svg)](https://github.com/yohanim/ha_tempo/releases)
[![License](https://img.shields.io/github/license/yohanim/ha_tempo.svg)](LICENSE.md)

[![Ouvrir votre instance Home Assistant et ajouter ce dépôt dans HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=yohanim&repository=ha_tempo&category=integration)

[![Ouvrir votre instance Home Assistant et configurer l'intégration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=tempo_rte_forecast)

Intégration complète pour le suivi du contrat Tempo (et autres) dans Home Assistant.

Elle récupère les données depuis plusieurs sources fiables pour fournir un ensemble complet de capteurs :
- **Couleurs Tempo J et J+1** depuis l'API open-data de RTE.
- **Prévisions de couleur J+2 à J+9** depuis [Open-DPE](https://open-dpe.fr/).
- **Prix de l'électricité** en temps réel selon votre contrat (Base, Heures Creuses, Tempo) et votre puissance souscrite, depuis les grilles officielles de [data.gouv.fr](https://www.data.gouv.fr/).

## 📦 Installation

Utilisez les boutons bleus ci-dessus pour installer l'intégration via HACS puis l'ajouter depuis la page des intégrations de Home Assistant.

**Installation manuelle** : Copiez le contenu du dossier `custom_components/tempo_rte_forecast/` dans votre dossier `custom_components` de Home Assistant, puis redémarrez.

## 🎯 Capteurs principaux

Cette intégration crée plusieurs capteurs pour une granularité maximale.

- **`sensor.rte_tempo_color_j`** : Affiche la couleur du jour actuel (ex: 🔵).
- **`sensor.rte_tempo_color_j_1`** : Affiche la couleur du lendemain (ex: ⚪).
- **`sensor.prix_actuel`** : Affiche le prix actuel du kWh en fonction de votre contrat et de la période en cours.
- **`sensor.prix_bleu_hp`**, **`sensor.prix_rouge_hc`**, etc. : Des capteurs dédiés pour chaque tarif de votre contrat.
- **`sensor.opendpe_j2`**, **`sensor.opendpe_j3`**, etc. : Les prévisions de couleur pour les jours à venir.

## 📊 Attributs disponibles

Les informations sont réparties sur les différents capteurs pour plus de clarté.

### `sensor.prix_actuel`

- `current_period`: "HP" ou "HC".
- `is_hc`: `true` si la période actuelle est en Heures Creuses.
- `contract`: Votre type de contrat (Base, Heures Creuses, Tempo).
- `tempo_color`: La couleur Tempo en cours si votre contrat est Tempo.
- `prices_last_update`: Date de la dernière mise à jour des grilles de prix.

### `sensor.rte_tempo_color_j` (et J+1)

- `date`: La date du jour concerné.
- `color`: Le nom de la couleur (Bleu, Blanc, Rouge).
- `is_red` / `is_white` / `is_blue`: `true` si la couleur correspond.

### `sensor.prix_bleu_hp` (et autres capteurs de prix spécifiques)

- `active`: `true` si ce tarif est celui qui est actuellement appliqué.
- `subscribed_power`: Votre puissance souscrite en kVA.

## 🤖 Exemples d'automatisations

### 1. Limiter la consommation en jour rouge HP

```yaml
automation:
  - alias: "Économie jour rouge HP"
    trigger:
      - platform: template
        value_template: "{{ is_state_attr('sensor.rte_tempo_color_j', 'is_red', true) and is_state_attr('sensor.prix_actuel', 'current_period', 'HP') }}"
    action:
      - service: climate.set_temperature
        target:
          entity_id: climate.chambre
        data:
          temperature: 18
      - service: switch.turn_off
        target:
          entity_id: switch.cumulus
```

### 2. Notification si demain sera rouge

```yaml
automation:
  - alias: "Alerte J+1 rouge"
    trigger:
      - platform: state
        entity_id: sensor.rte_tempo_color_j_1
        attribute: is_red
        to: true
    action:
      - service: notify.mobile_app
        data:
          title: "⚠️ Jour rouge demain"
          message: "Demain sera un jour rouge Tempo. Pensez à charger la voiture cette nuit !"
```

### 3. Basculement automatique en heures creuses

```yaml
automation:
  - alias: "Activation HC"
    trigger:
      - platform: state
        entity_id: sensor.prix_actuel
        attribute: is_hc
        to: true
    action:
      - service: switch.turn_on
        target:
          entity_id:
            - switch.cumulus
            - switch.charge_voiture
      - service: climate.set_temperature
        target:
          entity_id: climate.salon
        data:
          temperature: 21
```

### 4. Template pour afficher la couleur dans l'interface

```yaml
# Dans un card markdown
type: markdown
content: |
  ## Tempo aujourd'hui
  Couleur : **{{ states('sensor.rte_tempo_color_j') }}**
  Période : **{{ state_attr('sensor.prix_actuel', 'current_period') }}**

  ## Tempo demain
  Couleur : **{{ states('sensor.rte_tempo_color_j_1') }}**
```

### 5. Utiliser les attributs dans les conditions

```yaml
automation:
  - alias: "Action complexe"
    trigger:
      - platform: time
        at: "20:00:00"
    condition:
      - condition: template
        value_template: "{{ state_attr('sensor.edf_tempo', 'tomorrow_is_red') }}"
    action:
      - service: script.preparation_jour_rouge
```

## 🔄 Fonctionnement automatique

L'intégration se met à jour **automatiquement** aux moments clés :

### Mises à jour programmées (par défaut)

- **`tempo_day_change_time` (défaut 06:00)** : 🌅 Changement de jour Tempo.
  - Le capteur `sensor.rte_tempo_color_j` prend la couleur du nouveau jour.
  - Le capteur `sensor.prix_actuel` change de période si cette heure correspond à une transition HP/HC.

- **5 minutes avant le changement de jour** : 💰 Mise à jour des prix.
  - L'intégration vérifie si une nouvelle grille tarifaire est disponible sur data.gouv.fr (selon l'intervalle en jours que vous avez défini).

- **`rte_tempo_color_refresh_time` (défaut 07:05)** : 📡 Récupération API RTE de la couleur J+1.
  - Mise à jour du capteur `sensor.rte_tempo_color_j_1`.

- **`edf_tempo_color_refresh_time` (défaut 11:05)** : 📡 Nouvelle tentative de récupération API.

- **Plages d'heures creuses** : 🌙 Passage en Heures Creuses/Pleines.
  - Le capteur `sensor.prix_actuel` met à jour ses attributs `is_hc` et `current_period`.

## 🎨 Template Sensor pour simplifier les automatisations (optionnel)

Il est recommandé de créer des `template sensors` pour recréer des états combinés faciles à utiliser dans les automatisations.

```yaml
template:
  - binary_sensor:
      - name: "Jour Rouge HP"
        state: "{{ is_state_attr('sensor.rte_tempo_color_j', 'is_red', true) and is_state_attr('sensor.prix_actuel', 'current_period', 'HP') }}"
        icon: mdi:flash-alert

      - name: "Demain Rouge"
        state: "{{ is_state_attr('sensor.rte_tempo_color_j_1', 'is_red', true) }}"
        icon: mdi:calendar-alert

      - name: "Heures Creuses"
        state: "{{ is_state_attr('sensor.prix_actuel', 'is_hc', true) }}"
        icon: mdi:power-sleep
```

## 🐛 Support

Pour signaler un bug ou demander une fonctionnalité, ouvrez une issue sur GitHub.

## 📄 Licence

GNU GPL v3 © 2025 Kevin Gossent

Ce logiciel est distribué sous licence GNU General Public License v3.0. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

**Développé par Kevin Gossent**
**Développé par l'intégration de Christophe Bansart [https://github.com/chrisbansart/ha_tempo](https://github.com/chrisbansart/ha_tempo)**
