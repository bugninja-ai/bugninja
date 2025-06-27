**Member**
- id: str (CUID)
- user_id: ForeignKey[User]
- created_at: str
- role: Enum[admin, member, guest(read-only)]

**Organization**
- id: str (CUID)
- name: str
- created_at: datetime
- role: Enum[admin, member, guest(read-only)]
- logo: str(img)

**Project**
- id: str (CUID)
- organization_id: ForeignKey[Organization]
- name: str
- created_at: datetime
- default_url_route: str

An organization can have multiple Projects and multiple Members as well

**TestCase**
- id: str (CUID)
- project_id: ForeignKey[Project]
- created_at: datetime
- updated_at: datetime
- test_description: str
- extra_rules: str
- url_route: str
- allowed_domains: List[str]

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

