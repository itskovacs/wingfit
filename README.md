<p align="center"><img width="120" src="./src/public/favicon_square.png"></p>
<h2 align="center">Wingfit</h2>

<div align="center">

![Status](https://img.shields.io/badge/status-active-success?style=for-the-badge)
[![GitHub Issues](https://img.shields.io/github/issues/itskovacs/wingfit?style=for-the-badge&color=ededed)](https://github.com/itskovacs/wingfit/issues)
[![License](https://img.shields.io/badge/license-_CC_BY_NC_SA_4.0-2596be?style=for-the-badge)](/LICENSE)

<a href="https://apps.umbrel.com/app/wingfit" target="_blank"><img width="180" src="https://apps.umbrel.com/badge-light.svg"></a>

</div>

<p align="center">🏋️ The wingman for your fitness </p>
<br>

<div align="center">

![Wingfit Planning](./.github/screenshot.png)

</div>

## 📝 Table of Contents

- 📦 [About](#about)
- 🌱 [Getting Started](#getting_started)
- 📸 [Demo](#Demo)
- 🚧 [Roadmap](#Roadmap)
- 📜 [License](#License)
- 🤝 [Contributing](#Contributing)
- 🛠️ [Tech Stack](#techstack)

## 📦 About <a name = "about"></a>

Wingfit is a minimalist fitness app to **plan your workouts**, **track your personal records** and **leverage smartwatch data**.

Demo is worth a thousand words, head to 📸 [Demo](#Demo).

🔒 Privacy-First – No telemetry, no tracking, fully self-hostable. You own your data. Inspect, modify, and contribute freely.

<br>

## 🌱 Getting Started <a name = "getting_started"></a>

If you need help, feel free to open an [issue](https://github.com/itskovacs/wingfit/issues).

Deployment is designed to be simple using Docker.

### Option 1: Docker Compose (Recommended)

Use the `docker-compose.yml` file provided in this repository. No changes are required, though you may customize it to suit your needs.

Run the container:

```bash
docker-compose up -d
```

### Option 2: Docker Run

```bash
# Ensure you have the latest image
docker pull ghcr.io/itskovacs/wingfit:5

# Run the container
docker run -d -p 8080:8000 -v ./storage:/app/storage ghcr.io/itskovacs/wingfit:5
```

Refer to the [configuration documentation](https://github.com/itskovacs/wingfit/tree/main/docs/config.md) to set up OIDC authentication and other settings.

<br>

## 📸 Demo <a name = "demo"></a>

A demo is available at [Wingfit.fr](https://wingfit.fr).

<div align="center">

|         |         |
|:-------:|:-------:|
| ![](./.github/sc_planning.png) | ![](./.github/sc_blocs.png) |
| ![](./.github/sc_pr.png) | ![](./.github/sc_statistics.png) |
| ![](./.github/sc_programs.png) | ![](./.github/sc_program.png) |

</div>

<br>

## 🚧 Roadmap <a name = "roadmap"></a>

New features coming soon<sup>TM</sup>, check out the development plan in the [Roadmap Wiki](https://github.com/itskovacs/wingfit/wiki/Roadmap). If you have ideas 💡, feel free to open an issue.

If you want to develop new feature, feel free to open a pull request (see [🤝 Contributing](#contributing)).

<br>

## 📜 License <a name = "license"></a>

I decided to license Wingfit under the **CC BY-NC-SA 4.0** – You may use, modify, and share freely with attribution, but **commercial use is prohibited**.

<br>

## 🤝 Contributing <a name = "contributing"></a>

Contributions are welcome! Feel free to open issues if you find bugs and pull requests for your new features!

1. Fork the repo
2. Create a new branch (`my-new-wingfit-feature`)
3. Commit changes
4. Open a pull request

<br>

## 🛠️ Tech Stack <a name = "techstack"></a>

### **Frontend**

- 🅰️ Angular 19
- 🏗️ PrimeNG 19
- 🎨 Tailwind CSS 4

### **Backend**

- 🐍 FastAPI, SQLModel
- 🗃️ SQLite

<br>

<div align="center">

If you like Wingfit, consider giving it a **star** ⭐!  
Made with ❤️ in BZH  

<a href='https://ko-fi.com/itskovacs' target='_blank'><img height='36' style='border:0px;height:36px;' src='https://storage.ko-fi.com/cdn/kofi1.png' border='0' alt='Buy Me a Coffee at ko-fi.com' /></a>  
</div>
