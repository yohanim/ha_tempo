# Home Assistant - Tempo RTE Integration, Forecasts & Prices

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub release](https://img.shields.io/github/release/yohanim/ha_tempo.svg)](https://github.com/yohanim/ha_tempo/releases)
[![License](https://img.shields.io/github/license/yohanim/ha_tempo.svg)](LICENSE.md)

[![Open your Home Assistant instance and add this repository to HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=yohanim&repository=ha_tempo&category=integration)

[![Open your Home Assistant instance and configure the integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=tempo_rte_forecast)

Complete integration for tracking the EDF Tempo contract (and others) in Home Assistant.

It retrieves data from several reliable sources to provide a complete set of sensors:
- **Tempo Colors (Today and Tomorrow)** from the RTE open-data API.
- **Color Forecasts (J+2 to J+9)** from [Open-DPE](https://open-dpe.fr/).
- **Electricity Prices** in real-time according to your contract (Base, Off-peak/Peak, Tempo) and your subscribed power, from official [data.gouv.fr](https://www.data.gouv.fr/) grids.

---

## 📦 Installation

Use the blue buttons above to install the integration via HACS then add it from the Home Assistant integrations page.

**Manual installation**: Copy the contents of the `custom_components/tempo_rte_forecast/` folder to your Home Assistant `custom_components` folder, then restart.

---

## 🎯 Main Sensors

This integration creates several sensors for maximum granularity.

- **`sensor.tempo_color_j`**: Current day's color (e.g., 🔵).
- **`sensor.tempo_color_j1`**: Tomorrow's color (e.g., ⚪).
- **`sensor.tempo_color_j1_combined`**: Synthesized J+1 color (Uses RTE if known, otherwise fallback to Open-DPE forecast).
- **`sensor.current_price`**: Current kWh price based on your contract and period.
- **`sensor.price_hp_blue`**, **`sensor.price_hc_red`**, etc.: Dedicated sensors for each tariff of your contract.
- **`sensor.tempo_forecast_j2`**, **`sensor.tempo_forecast_j3`**, etc.: Color forecasts for upcoming days.

---

## 📊 Available Attributes

Information is distributed across different sensors for clarity.

### `sensor.current_price`
- `current_period`: "HP" (Peak) or "HC" (Off-peak).
- `is_hc`: `true` if the current period is Off-peak.
- `contract`: Your contract type (Base, Heures Creuses, Tempo).
- `tempo_color`: The current Tempo color if your contract is Tempo.
- `prices_last_update`: Date of the last price grid update.
- `subscribed_power`: Your subscribed power in kVA.

### `sensor.tempo_color_j` (and J+1)
- `date`: Date of the day concerned.
- `color`: Color name (Blue, White, Red).
- `is_red` / `is_white` / `is_blue`: `true` if the color matches.
- `color_emoji`: Emoji representing the color.
- `data_source`: "api", "cache", or "none".

### `sensor.tempo_color_j1_combined`
- `active_source`: "RTE" or "OpenDPE".
- `rte_status`: Status from RTE.
- `forecast_status`: Status from Open-DPE.

---

## 🤖 Automation Examples

### 1. Limit consumption during Red Peak hours
```yaml
automation:
  - alias: "Red Day Peak Energy Saving"
    trigger:
      - platform: template
        value_template: "{{ is_state_attr('sensor.tempo_color_j', 'is_red', true) and is_state_attr('sensor.current_price', 'current_period', 'HP') }}"
    action:
      - service: climate.set_temperature
        target:
          entity_id: climate.living_room
        data:
          temperature: 18
      - service: switch.turn_off
        target:
          entity_id: switch.water_heater
```

### 2. Notification if tomorrow will be Red
```yaml
automation:
  - alias: "Alert Red Day Tomorrow"
    trigger:
      - platform: state
        entity_id: sensor.tempo_color_j1
        attribute: is_red
        to: true
    action:
      - service: notify.mobile_app
        data:
          title: "⚠️ Red Day Tomorrow"
          message: "Tomorrow will be a Red Tempo day. Charge your EV tonight!"
```

### 3. Automatic activation during Off-Peak hours
```yaml
automation:
  - alias: "Off-Peak Activation"
    trigger:
      - platform: state
        entity_id: sensor.current_price
        attribute: is_hc
        to: true
    action:
      - service: switch.turn_on
        target:
          entity_id:
            - switch.water_heater
            - switch.ev_charger
      - service: climate.set_temperature
        target:
          entity_id: climate.living_room
        data:
          temperature: 21
```

### 4. Template Sensors (Optional)
```yaml
template:
  - binary_sensor:
      - name: "Red Day Peak"
        state: "{{ is_state_attr('sensor.tempo_color_j', 'is_red', true) and is_state_attr('sensor.current_price', 'current_period', 'HP') }}"
        icon: mdi:flash-alert

      - name: "Tomorrow Red"
        state: "{{ is_state_attr('sensor.tempo_color_j1', 'is_red', true) }}"
        icon: mdi:calendar-alert

      - name: "Off-Peak Hours"
        state: "{{ is_state_attr('sensor.current_price', 'is_hc', true) }}"
        icon: mdi:power-sleep
```

### 5. UI Markdown Card
```yaml
type: markdown
content: |
  ## Tempo Today
  Color: **{{ states('sensor.tempo_color_j') }} {{ state_attr('sensor.tempo_color_j', 'color_emoji') }}**
  Period: **{{ state_attr('sensor.current_price', 'current_period') }}**

  ## Tempo Tomorrow
  Color: **{{ states('sensor.tempo_color_j1') }} {{ state_attr('sensor.tempo_color_j1', 'color_emoji') }}**
```

---

## 🔄 Automatic Operation

The integration updates **automatically** at key moments:
- **06:00**: Tempo day change.
- **07:05**: RTE API J+1 color retrieval.
- **11:05**: Second RTE API attempt.
- **07:00 & 15:00**: Open-DPE forecast retrieval.
- **Off-peak transitions**: Transitions between Peak and Off-peak hours.

---
---

# Home Assistant - Intégration Tempo RTE, Prévisions & Prix

Intégration complète pour le suivi du contrat Tempo (et autres) dans Home Assistant.

Elle récupère les données depuis plusieurs sources fiables pour fournir un ensemble complet de capteurs :
- **Couleurs Tempo J et J+1** depuis l'API open-data de RTE.
- **Prévisions de couleur J+2 à J+9** depuis [Open-DPE](https://open-dpe.fr/).
- **Prix de l'électricité** en temps réel selon votre contrat (Base, Heures Creuses, Tempo) et votre puissance souscrite, depuis les grilles officielles de [data.gouv.fr](https://www.data.gouv.fr/).

---

## 📦 Installation

Utilisez les boutons bleus en haut de page pour installer l'intégration via HACS puis l'ajouter depuis la page des intégrations de Home Assistant.

**Installation manuelle** : Copiez le contenu du dossier `custom_components/tempo_rte_forecast/` dans votre dossier `custom_components` de Home Assistant, puis redémarrez.

---

## 🎯 Capteurs principaux

Cette intégration crée plusieurs capteurs pour une granularité maximale.

- **`sensor.tempo_color_j`** : Couleur du jour actuel (ex: 🔵).
- **`sensor.tempo_color_j1`** : Couleur du lendemain (ex: ⚪).
- **`sensor.tempo_color_j1_combined`** : Couleur J+1 synthétisée (Utilise RTE si connu, sinon repli sur la prévision Open-DPE).
- **`sensor.current_price`** : Prix actuel du kWh en fonction de votre contrat et de la période en cours.
- **`sensor.price_hp_blue`**, **`sensor.price_hc_red`**, etc. : Des capteurs dédiés pour chaque tarif de votre contrat.
- **`sensor.tempo_forecast_j2`**, **`sensor.tempo_forecast_j3`**, etc. : Les prévisions de couleur pour les jours à venir.

---

## 📊 Attributs disponibles

Les informations sont réparties sur les différents capteurs pour plus de clarté.

### `sensor.current_price`
- `current_period`: "HP" ou "HC".
- `is_hc`: `true` si la période actuelle est en Heures Creuses.
- `contract`: Votre type de contrat (Base, Heures Creuses, Tempo).
- `tempo_color`: La couleur Tempo en cours si votre contrat est Tempo.
- `prices_last_update`: Date de la dernière mise à jour des grilles de prix.
- `subscribed_power`: Votre puissance souscrite en kVA.

### `sensor.tempo_color_j` (et J+1)
- `date`: La date du jour concerné.
- `color`: Le nom de la couleur (Bleu, Blanc, Rouge).
- `is_red` / `is_white` / `is_blue`: `true` si la couleur correspond.
- `color_emoji`: Emoji représentant la couleur.
- `data_source`: "api", "cache", ou "none".

### `sensor.tempo_color_j1_combined`
- `active_source`: "RTE" ou "OpenDPE".
- `rte_status`: État venant de RTE.
- `forecast_status`: État venant d'Open-DPE.

---

## 🤖 Exemples d'automatisations

### 1. Limiter la consommation en jour rouge HP
```yaml
automation:
  - alias: "Économie jour rouge HP"
    trigger:
      - platform: template
        value_template: "{{ is_state_attr('sensor.tempo_color_j', 'is_red', true) and is_state_attr('sensor.current_price', 'current_period', 'HP') }}"
    action:
      - service: climate.set_temperature
        target:
          entity_id: climate.salon
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
        entity_id: sensor.tempo_color_j1
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
        entity_id: sensor.current_price
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

### 4. Template Sensors pour simplifier (optionnel)
```yaml
template:
  - binary_sensor:
      - name: "Jour Rouge HP"
        state: "{{ is_state_attr('sensor.tempo_color_j', 'is_red', true) and is_state_attr('sensor.current_price', 'current_period', 'HP') }}"
        icon: mdi:flash-alert

      - name: "Demain Rouge"
        state: "{{ is_state_attr('sensor.tempo_color_j1', 'is_red', true) }}"
        icon: mdi:calendar-alert

      - name: "Heures Creuses"
        state: "{{ is_state_attr('sensor.current_price', 'is_hc', true) }}"
        icon: mdi:power-sleep
```

### 5. Carte Markdown pour l'interface
```yaml
# Dans une carte Markdown
type: markdown
content: |
  ## Tempo aujourd'hui
  Couleur : **{{ states('sensor.tempo_color_j') }} {{ state_attr('sensor.tempo_color_j', 'color_emoji') }}**
  Période : **{{ state_attr('sensor.current_price', 'current_period') }}**

  ## Tempo demain
  Couleur : **{{ states('sensor.tempo_color_j1') }} {{ state_attr('sensor.tempo_color_j1', 'color_emoji') }}**
```

---

## 🔄 Fonctionnement automatique

L'intégration se met à jour **automatiquement** aux moments clés :
- **06:00** : Changement de jour Tempo.
- **07:05** : Récupération API RTE de la couleur J+1.
- **11:05** : Deuxième tentative API RTE.
- **07:00 & 15:00** : Récupération des prévisions Open-DPE.
- **Transitions HC/HP** : Passages entre Heures Pleines et Heures Creuses.

---

## 📄 Licence

GNU GPL v3 © 2025 Kevin Gossent

Ce logiciel est distribué sous licence GNU General Public License v3.0. Voir le fichier [LICENSE](LICENSE) pour plus de détails.
