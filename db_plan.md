**Member**
- id: str (CUID)
- user_id: ForeignKey[User]
- created_at: str
- role: Enum[admin, member, guest(read-only)]

**Organization**
- id: str (CUID)
- name: str
- created_at: datetime
- logo: str(img)

**Project**
- id: str (CUID)
- organization_id: ForeignKey[Organization]
- name: str
- created_at: datetime
- default_url_route: str

Okay, so the three main tables that our database will be working with are the organization, the project, and the member. The relationships are rather straightforward: members are connected in Supabase, with data linked to users that registered to the platform. Organization represents an organization that is created by a user, and an organization can have multiple projects.
An organization can have multiple Projects and multiple Members as well.
A single Project can have multiple TestCases

**Document**
- id: str (CUID)
- test_case_id: Optional[ForeignKey[TestCase]]
- project_id: ForeignKey[Project]
- name: str
- created_at: datetime
- content: str

A Project can have multiple Documents but a Document can only belong to a single Project.

**TestCase**
- id: str (CUID)
- project_id: ForeignKey[Project]
- document_id: Optional[ForeignKey[Document]]
- created_at: datetime
- updated_at: datetime
- test_description: str
- extra_rules: str
- url_route: str
- allowed_domains: List[str]

A single TestCase can belong to a single Project, but a Project can have multiple TestCases.
A TestCase might belong to a Document (and vice versa) but it is not necessary.

**Tag**
- id: str (CUID)
- project_id: ForeignKey[Project]
- name: str
- color: str

A member of an organization can create projects, and for these projects, they can create documents, test cases, and tags as well. Documents and test cases can be related to each other, and they are in a one-to-one relationship. A single project can have multiple documents and multiple test cases at the same time, and tags are connected to test cases. I know it's a many-to-many relationship, so one tag can connect to multiple test cases, and one test case can have multiple tags. Therefore, an association table is needed here, and a project can have multiple tags.

There is a many-to-many connection between Tags and TestCases so we might need an association table. Every Tag belongs to a Project, but one project can have multiple Tags.

**SecretValue**
- id: str (CUID)
- project_id: ForeignKey[Project]
- created_at: datetime
- updated_at: datetime
- secret_name: Unique[str]
- secret_value: str
- version: int

**TestTraversal**
- id: str (CUID)
- test_case_id: ForeignKey[TestCase]
- browser_config_id: ForeignKey[BrowserConfig]
- expected_outcome: str
- created_at: datetime
- version: int

A SecretValue belongs to a single Project, but one Project can have multiple SecretValues.
A SecretValue can belong to multiple TestTraversal, and a TestTraversal  can have multiple SecretValues so a many to many association table might be in order.

**BrowserConfig**
- id: str (CUID)
- created_at: datetime
- updated_at: datetime
- browser_config: JSON

A TestCase can have multiple BrowserConfigs, and the BrowserConfig can also belong to multiple TestCases. Therefore, there should be a many-to-many connection between the two tables, probably with an association table. Additionally, a BrowserConfig can belong to multiple TestTraversals, whereas a single test traversal can only have one BrowserConfig.

The TestCase can have multiple test traversals. Test traversals describe a potential set of combinations of input values and expected output values for a specific test. For example, a test traversal can have multiple secret values, but a secret value can belong to multiple test traversals as well. A test traversal can and must have at least one browser config, but one browser config can belong to multiple test traversals. Between the test cases and browser configs, there can be many relationships because a browser config can belong to multiple test cases, and a test case can have multiple browser configs as well.


**BrainState**
- id: str (CUID)
- test_traversal_id: ForeignKey[TestTraversal]
- idx_in_traversal: int
- valid: bool
- evaluation_previous_goal: str
- memory: str
- next_goal: str

A single TestTraversal can have multiple BrainStates, however a BrainState only belongs to a single TestTraversal.

**Action**
- id: str (CUID)
- brain_state_id: ForeignKey[BrainState]
- idx_in_brain_state: int
- action: JSON
- dom_element_data: JSON

Every action belongs to a single BrainState, but a single BrainState can have multiple actions!


Test traversals are made up of different brain states. Brain states represent specific AI agent thinking processes, and these brain states are made up of different actions that the agent performs. Test traversals can have multiple brain states, and each brain state is made up of multiple.

**HistoryElement**
- id: str (CUID)
- test_run_id: FK[TestRun]
- action_id: FK[Action]
- action_started_at: datetime
- action_finished_at: datetime
- history_element_state: Enum[PASSED, FAILED]
- screenshot: str (img)

EveryHistoryElement can belong to exactly a single Action and a single TestRun! However Actions and TestRuns can have multiple history elements


**TestRun**
- id: str (CUID)
- test_traversal_id: ForeignKey[TestTraversal]
- test_config_id: ForeignKey[TestConfig]
- cost_id: Optional[ForeignKey[TestConfig]]
- run_type: Enum[AGENTIC, REPLAY]
- repair_was_needed: bool
- started_at: datetime
- finished_at: datetime
- state: Enum[PASSED, RUNNING, FAILED]
- history: OrderedList[HistoryElement]
- run_gif: str (gif)

A multiple TestRun can belong to a single TestTraversal, however every TestRun belongs to just a single TestTraversal.

**Cost**
- id: str (CUID)
- test_run_id: FK[TestRun]
- project_id: FK[Project]
- created_at: datetime
- model_type: str
- cost_per_token: float
- input_token_num: int
- completion_token_num: int
- cost_in_dollars: float

A test run represents a running version of a test traversal. A test traversal can have multiple test runs. However, a single test run can only be related to a single test traversal. Test runs have multiple history elements. These history elements are related to specific actions. However, actions can be related to multiple history elements. Test runs also have costs, which are stored in the cost table. And there are test runs that have no costs. Therefore, the foreign key relating to the cost table is optional in the test run. However, every cost must have a test run. Also, costs are related to the project as well.
There is a one to one relationship between Cost table and a single TestRun, however not every TestRun have an associated cost