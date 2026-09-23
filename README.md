# Interactive Quiz Portal & Automated Gradebook

A lightweight, serverless platform for hosting interactive language exercises and automatically logging student results to a private Google Sheet.

The system uses [H5P](https://h5p.org/) via the free desktop editor [Lumi](https://lumi.education/) to build activities, hosts them statically via GitHub Pages, and uses a custom webhook to extract student scores and mistakes without requiring an external Learning Management System (LMS).

## How It Works

```
[Teacher builds in Lumi]
         ↓ exports standalone HTML
[Drop HTML into /quizzes]
         ↓ pushes to GitHub
[GitHub Actions]
         ↓ injects tracker.js + deploys to GitHub Pages
[Student completes test online]
         ↓ browser catches xAPI score & mistakes
[Google Sheets Webhook]
         ↓ logs score + highlights mistakes in RED
```

- **Authoring**: Quizzes are authored offline using Lumi and exported as standalone HTML bundles.
- **Auto-Injection & Deployment**: When an HTML file is uploaded to `/quizzes`, a GitHub Action automatically injects `tracker.js` before the closing `</body>` tag, runs `generate_index.py` to update the portal with all quizzes and 'Copy link' buttons, and publishes the site to GitHub Pages.
- **Portal & Sharing**: The landing page at `https://<username>.github.io/<repo-name>/` provides a clean, searchable index of all quizzes with instant "Copy link" buttons for sharing.
- **Automated Error Logging**: Upon quiz submission, the injected script captures the student's name, activity name, score, and the exact sentences containing mistakes.
- **Google Sheets Log**: Incorrect student responses are appended to a Google Sheet with mistaken words highlighted in red text.

## Repository Structure

```
├── quizzes/              # Drop raw exported Lumi HTML files here
│   └── example-quiz.html
├── build_public.py       # Prepares public/ distribution folder and injects tracker.js
├── generate_index.py     # Automatically scans quizzes and generates the portal
├── index.html            # Minimal and clean quiz portal (root preview)
├── tracker.js            # Standalone listener that intercepts H5P xAPI events
├── apps_script_webhook.gs # Google Apps Script webhook code for Google Sheets logging
├── .github/
│   └── workflows/
│       └── deploy.yml    # Injects tracker.js, builds portal, and deploys to Pages
└── README.md
```

## Workflow for Teachers

### 1. Build the Exercise
- Create your exercise in Lumi (e.g., Fill in the Blanks, Drag and Drop).
- Export via **File > Export > HTML** (all-in-one bundle).
- Name the file cleanly using lowercase letters and hyphens (e.g., `adjektive-1.html`).

### 2. Upload to GitHub
- Go to the repository on GitHub.com.
- Navigate into the `quizzes` folder.
- Click **Add file > Upload files**, drag your HTML file in, and click **Commit changes**.

### 3. Share with Students
Within ~60 seconds, the new exercise is automatically indexed:
- **Quiz Portal**:
  ```
  https://<username>.github.io/<repo-name>/
  ```
  Visit the portal to browse exercises, filter by title, and click **Copy link** to easily get shareable links for students.
- **Direct Exercise Link**:
  ```
  https://<username>.github.io/<repo-name>/<file-name>.html
  ```
Students enter their name when prompted and complete the task.

### 4. Review Results
Open the connected Google Sheet to review:
- **Timestamp**
- **Student Name**
- **Activity Name**
- **Score / Max Score**
- **Incorrect Sentences** (with the student's error highlighted in red)

## Setup Instructions

### 1. Google Sheets Webhook
1. Create a new Google Sheet with the following headers in Row 1:
   ```
   Timestamp | Student | Activity | Score | Max Score | Mistakes
   ```
2. Open **Extensions > Apps Script**, paste the contents of `apps_script_webhook.gs`, and save.
3. Deploy as a Web App:
   - **Execute as**: Me
   - **Who has access**: Anyone
4. Copy the generated Web App URL (`.../exec`).

### 2. Repository Configuration
1. Add the Google Web App URL to your repository secrets as `WEBHOOK_URL` (or paste it into `tracker.js`).
2. (Optional) Add your Google Sheet URL to repository secrets as `RESULTS_URL`.
3. Ensure `.github/workflows/deploy.yml` is enabled.
4. Under **Settings > Pages > Build and deployment > Source**, select **GitHub Actions**.
