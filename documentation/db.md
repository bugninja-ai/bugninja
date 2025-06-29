Great! Here's a clean, structured, and readable **database documentation** based on your original description. This includes:

* An overview of the entities.
* Key relationships.
* Proper use of Markdown formatting for clarity.
* Diagrams in Mermaid syntax to help visualize complex relationships.

---

# 📘 Database Documentation

## 🔹 Overview

This database supports an AI-driven testing platform. Users are organized into **Organizations**, which can manage multiple **Projects**. Each project consists of **Documents**, **Test Cases**, **Tags**, **Secrets**, and **Test Runs**. Test runs contain rich metadata including **Test Traversals**, **Brain States**, **Actions**, and **Costs**.

---

## 🧱 Core Entities

### **User** (external system - not defined here)

Represents the registered users. `Member.user_id` links to this.

---

### **Organization**

* `id`: CUID
* `name`: string
* `created_at`: datetime
* `logo`: string (image)

📌 **Relationships**:

* Has many `Members`
* Has many `Projects`

---

### **Member**

* `id`: CUID
* `user_id`: FK → User
* `created_at`: datetime
* `role`: Enum\[`admin`, `member`, `guest`]

📌 **Belongs to** an `Organization` (via logic not shown, assumed via Project access or implied).

---

### **Project**

* `id`: CUID
* `organization_id`: FK → Organization
* `name`: string
* `created_at`: datetime
* `default_url_route`: string

📌 **Relationships**:

* Has many `Documents`
* Has many `TestCases`
* Has many `Tags`
* Has many `SecretValues`
* Has many `Costs`

---

### **Document**

* `id`: CUID
* `project_id`: FK → Project
* `test_case_id`: (optional) FK → TestCase
* `name`: string
* `created_at`: datetime
* `content`: string

📌 A Document belongs to one Project and optionally links to a TestCase (1:1).

---

### **TestCase**

* `id`: CUID
* `project_id`: FK → Project
* `document_id`: optional FK → Document
* `created_at`: datetime
* `updated_at`: datetime
* `test_description`: string
* `extra_rules`: string
* `url_route`: string
* `allowed_domains`: list\[string]

📌 Relationships:

* Has many `Tags` (via junction table)
* Has many `TestTraversals`
* Has many `BrowserConfigs` (many-to-many)

---

### **Tag**

* `id`: CUID
* `project_id`: FK → Project
* `name`: string
* `color`: string

📌 Relationships:

* Many-to-many with `TestCase`

---

### **TagTestCase** (association table)

* `tag_id`: FK → Tag
* `test_case_id`: FK → TestCase

---

### **SecretValue**

* `id`: CUID
* `project_id`: FK → Project
* `created_at`, `updated_at`: datetime
* `secret_name`: string (unique)
* `secret_value`: string
* `version`: int

📌 Relationships:

* Many-to-many with `TestTraversal`

---

### **SecretValueTraversal** (association table)

* `secret_value_id`: FK → SecretValue
* `test_traversal_id`: FK → TestTraversal

---

### **BrowserConfig**

* `id`: CUID
* `created_at`, `updated_at`: datetime
* `browser_config`: JSON

📌 Relationships:

* Many-to-many with `TestCase`
* One-to-many with `TestTraversal`

---

### **TestCaseBrowserConfig** (association table)

* `test_case_id`: FK → TestCase
* `browser_config_id`: FK → BrowserConfig

---

### **TestTraversal**

* `id`: CUID
* `test_case_id`: FK → TestCase
* `browser_config_id`: FK → BrowserConfig
* `expected_outcome`: string
* `created_at`: datetime
* `version`: int

📌 Relationships:

* Has many `BrainStates`
* Has many `SecretValues` (many-to-many)
* Has many `TestRuns`

---

### **BrainState**

* `id`: CUID
* `test_traversal_id`: FK → TestTraversal
* `idx_in_traversal`: int
* `valid`: bool
* `evaluation_previous_goal`: string
* `memory`: string
* `next_goal`: string

📌 Relationships:

* Has many `Actions`

---

### **Action**

* `id`: CUID
* `brain_state_id`: FK → BrainState
* `idx_in_brain_state`: int
* `action`: JSON
* `dom_element_data`: JSON

📌 Relationships:

* Has many `HistoryElements`

---

### **TestRun**

* `id`: CUID
* `test_traversal_id`: FK → TestTraversal
* `test_config_id`: FK → TestConfig
* `cost_id`: Optional FK → Cost
* `run_type`: Enum\[`AGENTIC`, `REPLAY`]
* `repair_was_needed`: bool
* `started_at`, `finished_at`: datetime
* `state`: Enum\[`PASSED`, `RUNNING`, `FAILED`]
* `run_gif`: string (gif)

📌 Relationships:

* Has many `HistoryElements`
* Has one `Cost`

---

### **HistoryElement**

* `id`: CUID
* `test_run_id`: FK → TestRun
* `action_id`: FK → Action
* `action_started_at`: datetime
* `action_finished_at`: datetime
* `history_element_state`: Enum\[`PASSED`, `FAILED`]
* `screenshot`: string (image)

---

### **Cost**

* `id`: CUID
* `test_run_id`: FK → TestRun
* `project_id`: FK → Project
* `created_at`: datetime
* `model_type`: string
* `cost_per_token`: float
* `input_token_num`: int
* `completion_token_num`: int
* `cost_in_dollars`: float

---


## ✅ Notes

* All `id` fields are assumed to be CUIDs unless otherwise noted.
* Many-to-many relationships are explicitly documented with association tables.
* Optional foreign keys are clearly marked.
