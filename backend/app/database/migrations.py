"""
Safe database schema migrations for SQLite.
Inspects existing tables and automatically adds any missing columns without data loss.
"""

from sqlalchemy import text
from sqlalchemy.engine import Engine


def run_migrations(engine: Engine):
    """
    Performs safe dynamic column additions to existing SQLite tables and creates new relational tables.
    """
    with engine.connect() as conn:
        def get_existing_columns(table_name: str) -> set:
            try:
                res = conn.execute(text(f"PRAGMA table_info({table_name});"))
                return {row[1] for row in res.fetchall()}
            except Exception:
                return set()

        def table_exists(table_name: str) -> bool:
            try:
                res = conn.execute(text(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';"))
                return bool(res.fetchone())
            except Exception:
                return False

        # 1. Check & Upgrade 'projects'
        p_cols = get_existing_columns("projects")
        if p_cols:
            migrations = [
                ("client_id", "INTEGER REFERENCES clients(id) ON DELETE SET NULL"),
                ("status", "VARCHAR(50) DEFAULT 'PLANNING'"),
                ("start_date", "VARCHAR(50)"),
                ("expected_completion_date", "VARCHAR(50)"),
                ("actual_completion_date", "VARCHAR(50)"),
                ("budget", "FLOAT DEFAULT 0.0"),
                ("project_value", "FLOAT DEFAULT 0.0"),
                ("amount_received", "FLOAT DEFAULT 0.0"),
                ("amount_pending", "FLOAT DEFAULT 0.0"),
                ("show_qr", "BOOLEAN DEFAULT 1"),
                ("vr_type", "VARCHAR(50) DEFAULT 'external'"),
                ("vr_build_entry", "VARCHAR(1000)"),
            ]
            for col_name, col_def in migrations:
                if col_name not in p_cols:
                    try:
                        conn.execute(text(f"ALTER TABLE projects ADD COLUMN {col_name} {col_def};"))
                        print(f"[DB MIGRATION] Added column 'projects.{col_name}'")
                    except Exception as e:
                        print(f"[DB MIGRATION NOTE] projects.{col_name}: {e}")

        # 2. Check & Upgrade 'project_media'
        pm_cols = get_existing_columns("project_media")
        if pm_cols:
            migrations = [
                ("title", "VARCHAR(255)"),
                ("version", "VARCHAR(50) DEFAULT 'v1'"),
                ("uploaded_by", "VARCHAR(100)"),
                ("updated_at", "DATETIME"),
                ("vr_url", "VARCHAR(1000)"),
                ("has_vr", "BOOLEAN DEFAULT 0"),
                ("show_qr", "BOOLEAN DEFAULT 0"),
                ("vr_type", "VARCHAR(50) DEFAULT 'external'"),
                ("vr_build_entry", "VARCHAR(1000)"),
            ]
            for col_name, col_def in migrations:
                if col_name not in pm_cols:
                    try:
                        conn.execute(text(f"ALTER TABLE project_media ADD COLUMN {col_name} {col_def};"))
                        print(f"[DB MIGRATION] Added column 'project_media.{col_name}'")
                    except Exception as e:
                        print(f"[DB MIGRATION NOTE] project_media.{col_name}: {e}")

        # 3. Check & Upgrade 'blueprint_drawings'
        bp_cols = get_existing_columns("blueprint_drawings")
        if bp_cols:
            migrations = [
                ("version", "VARCHAR(50) DEFAULT 'v1'"),
                ("status", "VARCHAR(50) DEFAULT 'APPROVED'"),
                ("notes", "TEXT"),
                ("uploaded_by", "VARCHAR(100)"),
                ("is_published", "BOOLEAN DEFAULT 1"),
            ]
            for col_name, col_def in migrations:
                if col_name not in bp_cols:
                    try:
                        conn.execute(text(f"ALTER TABLE blueprint_drawings ADD COLUMN {col_name} {col_def};"))
                        print(f"[DB MIGRATION] Added column 'blueprint_drawings.{col_name}'")
                    except Exception as e:
                        print(f"[DB MIGRATION NOTE] blueprint_drawings.{col_name}: {e}")

        # 4. Check & Upgrade 'visualization_spaces'
        vs_cols = get_existing_columns("visualization_spaces")
        if vs_cols:
            migrations = [
                ("notes", "TEXT"),
                ("version", "VARCHAR(50) DEFAULT 'v1'"),
                ("status", "VARCHAR(50) DEFAULT 'APPROVED'"),
                ("show_qr", "BOOLEAN DEFAULT 1"),
                ("vr_type", "VARCHAR(50) DEFAULT 'external'"),
                ("vr_build_entry", "VARCHAR(1000)"),
            ]
            for col_name, col_def in migrations:
                if col_name not in vs_cols:
                    try:
                        conn.execute(text(f"ALTER TABLE visualization_spaces ADD COLUMN {col_name} {col_def};"))
                        print(f"[DB MIGRATION] Added column 'visualization_spaces.{col_name}'")
                    except Exception as e:
                        print(f"[DB MIGRATION NOTE] visualization_spaces.{col_name}: {e}")

        # 4b. Check & Upgrade 'visualization_media'
        vm_cols = get_existing_columns("visualization_media")
        if vm_cols:
            migrations = [
                ("show_qr", "BOOLEAN DEFAULT 0"),
                ("vr_type", "VARCHAR(50) DEFAULT 'external'"),
                ("vr_build_entry", "VARCHAR(1000)"),
            ]
            for col_name, col_def in migrations:
                if col_name not in vm_cols:
                    try:
                        conn.execute(text(f"ALTER TABLE visualization_media ADD COLUMN {col_name} {col_def};"))
                        print(f"[DB MIGRATION] Added column 'visualization_media.{col_name}'")
                    except Exception as e:
                        print(f"[DB MIGRATION NOTE] visualization_media.{col_name}: {e}")

        # 5. Check & Upgrade 'project_enquiries'
        enq_cols = get_existing_columns("project_enquiries")
        if enq_cols:
            migrations = [
                ("converted_client_id", "INTEGER REFERENCES clients(id) ON DELETE SET NULL"),
            ]
            for col_name, col_def in migrations:
                if col_name not in enq_cols:
                    try:
                        conn.execute(text(f"ALTER TABLE project_enquiries ADD COLUMN {col_name} {col_def};"))
                        print(f"[DB MIGRATION] Added column 'project_enquiries.{col_name}'")
                    except Exception as e:
                        print(f"[DB MIGRATION NOTE] project_enquiries.{col_name}: {e}")

        # 6. Check & Upgrade 'project_tasks'
        if table_exists("project_tasks"):
            task_info = conn.execute(text("PRAGMA table_info(project_tasks);")).fetchall()
            task_cols = {row[1] for row in task_info}
            proj_col_info = next((row for row in task_info if row[1] == "project_id"), None)

            # If project_id is NOT NULL, recreate table to allow nullable project_id
            if proj_col_info and proj_col_info[3] == 1:
                try:
                    conn.execute(text("""
                        CREATE TABLE project_tasks_migrated (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
                            created_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                            title VARCHAR(255) NOT NULL,
                            description TEXT,
                            assigned_to VARCHAR(100),
                            visibility VARCHAR(50) DEFAULT 'WORKSPACE' NOT NULL,
                            priority VARCHAR(50) DEFAULT 'MEDIUM' NOT NULL,
                            status VARCHAR(50) DEFAULT 'TODO' NOT NULL,
                            start_date DATETIME,
                            due_date DATETIME,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                        );
                    """))
                    conn.execute(text("""
                        INSERT INTO project_tasks_migrated (id, project_id, created_by_id, title, description, assigned_to, visibility, priority, status, start_date, due_date, created_at, updated_at)
                        SELECT id, project_id, created_by_id, title, description, assigned_to, coalesce(visibility, 'WORKSPACE'), coalesce(priority, 'MEDIUM'), coalesce(status, 'TODO'), start_date, due_date, created_at, updated_at
                        FROM project_tasks;
                    """))
                    conn.execute(text("DROP TABLE project_tasks;"))
                    conn.execute(text("ALTER TABLE project_tasks_migrated RENAME TO project_tasks;"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_project_tasks_id ON project_tasks (id);"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_project_tasks_project_id ON project_tasks (project_id);"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_project_tasks_created_by_id ON project_tasks (created_by_id);"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_project_tasks_visibility ON project_tasks (visibility);"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_project_tasks_priority ON project_tasks (priority);"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_project_tasks_status ON project_tasks (status);"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_project_tasks_due_date ON project_tasks (due_date);"))
                    print("[DB MIGRATION] Migrated 'project_tasks' schema: project_id is now nullable")
                except Exception as e:
                    print(f"[DB MIGRATION NOTE] project_tasks rebuild: {e}")
            else:
                task_migrations = [
                    ("created_by_id", "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
                    ("visibility", "VARCHAR(50) DEFAULT 'WORKSPACE'"),
                    ("start_date", "DATETIME"),
                ]
                for col_name, col_def in task_migrations:
                    if col_name not in task_cols:
                        try:
                            conn.execute(text(f"ALTER TABLE project_tasks ADD COLUMN {col_name} {col_def};"))
                            print(f"[DB MIGRATION] Added column 'project_tasks.{col_name}'")
                        except Exception as e:
                            print(f"[DB MIGRATION NOTE] project_tasks.{col_name}: {e}")

                # Ensure visibility defaults to WORKSPACE for any null rows
                try:
                    conn.execute(text("UPDATE project_tasks SET visibility = 'WORKSPACE' WHERE visibility IS NULL OR visibility = '';"))
                except Exception:
                    pass

        # 7. Create 'task_assignments' table if not exists
        if not table_exists("task_assignments"):
            try:
                conn.execute(text("""
                    CREATE TABLE task_assignments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        task_id INTEGER NOT NULL REFERENCES project_tasks(id) ON DELETE CASCADE,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    );
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_task_assignments_task_id ON task_assignments (task_id);"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_task_assignments_user_id ON task_assignments (user_id);"))
                print("[DB MIGRATION] Created table 'task_assignments'")
            except Exception as e:
                print(f"[DB MIGRATION NOTE] task_assignments: {e}")

        # 8. Create 'task_comments' table if not exists
        if not table_exists("task_comments"):
            try:
                conn.execute(text("""
                    CREATE TABLE task_comments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        task_id INTEGER NOT NULL REFERENCES project_tasks(id) ON DELETE CASCADE,
                        user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                        author_name VARCHAR(100) NOT NULL,
                        content TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    );
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_task_comments_task_id ON task_comments (task_id);"))
                print("[DB MIGRATION] Created table 'task_comments'")
            except Exception as e:
                print(f"[DB MIGRATION NOTE] task_comments: {e}")

        # 9. Task data reconciliation: link legacy assigned_to text and creator
        try:
            # Default creator to first active user if missing
            res_user = conn.execute(text("SELECT id, username FROM users ORDER BY id ASC LIMIT 1;")).fetchone()
            first_user_id = res_user[0] if res_user else None

            if first_user_id:
                conn.execute(text(f"UPDATE project_tasks SET created_by_id = {first_user_id} WHERE created_by_id IS NULL;"))

            # Reconcile text assigned_to to task_assignments
            all_users = conn.execute(text("SELECT id, username FROM users;")).fetchall()
            user_map = {u[1].strip().lower(): u[0] for u in all_users if u[1]}

            existing_tasks = conn.execute(text("SELECT id, assigned_to FROM project_tasks WHERE assigned_to IS NOT NULL AND assigned_to != '';")).fetchall()
            for t_id, t_assignee in existing_tasks:
                if not t_assignee:
                    continue
                clean_name = t_assignee.strip().lower()
                matched_uid = user_map.get(clean_name)
                if matched_uid:
                    # Check if assignment already exists
                    has_assign = conn.execute(text(f"SELECT id FROM task_assignments WHERE task_id = {t_id} AND user_id = {matched_uid};")).fetchone()
                    if not has_assign:
                        conn.execute(text(f"INSERT INTO task_assignments (task_id, user_id, assigned_at) VALUES ({t_id}, {matched_uid}, CURRENT_TIMESTAMP);"))
        except Exception as e:
            print(f"[DB MIGRATION NOTE] Task reconciliation: {e}")

        # 10. Check & Upgrade 'portfolio_categories' and 'portfolio_subcategories'
        if not table_exists("portfolio_categories"):
            try:
                conn.execute(text("""
                    CREATE TABLE portfolio_categories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name VARCHAR(100) NOT NULL UNIQUE,
                        slug VARCHAR(120) NOT NULL UNIQUE,
                        description TEXT,
                        display_order INTEGER DEFAULT 0 NOT NULL,
                        is_active BOOLEAN DEFAULT 1 NOT NULL,
                        is_default BOOLEAN DEFAULT 0 NOT NULL,
                        puzzle_size VARCHAR(50) DEFAULT 'small' NOT NULL,
                        cover_image VARCHAR(500),
                        featured_project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    );
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_portfolio_categories_id ON portfolio_categories (id);"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_portfolio_categories_slug ON portfolio_categories (slug);"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_portfolio_categories_display_order ON portfolio_categories (display_order);"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_portfolio_categories_is_active ON portfolio_categories (is_active);"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_portfolio_categories_featured_project_id ON portfolio_categories (featured_project_id);"))
                print("[DB MIGRATION] Created table 'portfolio_categories'")
            except Exception as e:
                print(f"[DB MIGRATION NOTE] portfolio_categories: {e}")

        if not table_exists("portfolio_subcategories"):
            try:
                conn.execute(text("""
                    CREATE TABLE portfolio_subcategories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        category_id INTEGER NOT NULL REFERENCES portfolio_categories(id) ON DELETE CASCADE,
                        name VARCHAR(100) NOT NULL,
                        slug VARCHAR(120) NOT NULL,
                        display_order INTEGER DEFAULT 0 NOT NULL,
                        is_active BOOLEAN DEFAULT 1 NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        CONSTRAINT uq_category_subcategory UNIQUE (category_id, name)
                    );
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_portfolio_subcategories_id ON portfolio_subcategories (id);"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_portfolio_subcategories_category_id ON portfolio_subcategories (category_id);"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_portfolio_subcategories_slug ON portfolio_subcategories (slug);"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_portfolio_subcategories_display_order ON portfolio_subcategories (display_order);"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_portfolio_subcategories_is_active ON portfolio_subcategories (is_active);"))
                print("[DB MIGRATION] Created table 'portfolio_subcategories'")
            except Exception as e:
                print(f"[DB MIGRATION NOTE] portfolio_subcategories: {e}")

        # Ensure 'featured_project_id' exists on 'portfolio_categories'
        cat_cols = get_existing_columns("portfolio_categories")
        if cat_cols and "featured_project_id" not in cat_cols:
            try:
                conn.execute(text("ALTER TABLE portfolio_categories ADD COLUMN featured_project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL;"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_portfolio_categories_featured_project_id ON portfolio_categories (featured_project_id);"))
                print("[DB MIGRATION] Added column 'portfolio_categories.featured_project_id'")
            except Exception as e:
                print(f"[DB MIGRATION NOTE] portfolio_categories.featured_project_id: {e}")

        # Ensure 'category_id' and 'subcategory_id' exist on 'projects'
        p_cols = get_existing_columns("projects")
        if p_cols:
            if "category_id" not in p_cols:
                try:
                    conn.execute(text("ALTER TABLE projects ADD COLUMN category_id INTEGER REFERENCES portfolio_categories(id) ON DELETE SET NULL;"))
                    print("[DB MIGRATION] Added column 'projects.category_id'")
                except Exception as e:
                    print(f"[DB MIGRATION NOTE] projects.category_id: {e}")
            if "subcategory_id" not in p_cols:
                try:
                    conn.execute(text("ALTER TABLE projects ADD COLUMN subcategory_id INTEGER REFERENCES portfolio_subcategories(id) ON DELETE SET NULL;"))
                    print("[DB MIGRATION] Added column 'projects.subcategory_id'")
                except Exception as e:
                    print(f"[DB MIGRATION NOTE] projects.subcategory_id: {e}")

        # 11. Seed Core Authoritative Portfolio Categories if empty
        try:
            cat_count = conn.execute(text("SELECT count(*) FROM portfolio_categories;")).fetchone()[0]
            if cat_count == 0:
                core_categories = [
                    (
                        "Residential",
                        "residential",
                        "Luxury private residences, bespoke villas, modern apartments, and penthouse living environments.",
                        1,
                        1,
                        1,
                        "large",
                        "/uploads/projects/residential.webp",
                        ["Apartment", "Villa", "Penthouse", "Private Residence", "Duplex"]
                    ),
                    (
                        "Commercial",
                        "commercial",
                        "Corporate headquarters, brand experience centers, flagship commercial venues, and coworking spaces.",
                        2,
                        1,
                        1,
                        "wide",
                        "/uploads/projects/commercial.webp",
                        ["Corporate HQ", "Showroom", "Experience Center", "Coworking", "Commercial Complex"]
                    ),
                    (
                        "Hospitality",
                        "hospitality",
                        "Fine dining restaurants, boutique cafés, destination hotels, resort retreats, and signature lounges.",
                        3,
                        1,
                        1,
                        "tall",
                        "/uploads/projects/hospitality.webp",
                        ["Restaurant", "Café", "Hotel", "Resort", "Bar & Lounge"]
                    ),
                    (
                        "Office",
                        "office",
                        "Ergonomic corporate offices, creative ateliers, executive boardrooms, and executive workspaces.",
                        4,
                        1,
                        1,
                        "wide",
                        "/uploads/projects/office.webp",
                        ["Design Studio", "Corporate Office", "Executive Suite", "Branch Office"]
                    ),
                    (
                        "Retail",
                        "retail",
                        "Bespoke retail ateliers, luxury fashion boutiques, curated galleries, and concept stores.",
                        5,
                        1,
                        1,
                        "small",
                        "/uploads/projects/retail.webp",
                        ["Flagship Atelier", "Boutique", "Art Gallery", "Concept Store"]
                    ),
                ]
                for name, slug, desc, order, active, default, size, cover, subcats in core_categories:
                    conn.execute(text("""
                        INSERT INTO portfolio_categories (name, slug, description, display_order, is_active, is_default, puzzle_size, cover_image)
                        VALUES (:name, :slug, :desc, :order, :active, :default, :size, :cover);
                    """), {"name": name, "slug": slug, "desc": desc, "order": order, "active": active, "default": default, "size": size, "cover": cover})
                    cat_id = conn.execute(text("SELECT id FROM portfolio_categories WHERE slug = :slug;"), {"slug": slug}).fetchone()[0]
                    for s_idx, s_name in enumerate(subcats):
                        s_slug = s_name.lower().replace(" ", "-").replace("&", "and")
                        conn.execute(text("""
                            INSERT INTO portfolio_subcategories (category_id, name, slug, display_order, is_active)
                            VALUES (:cat_id, :name, :slug, :order, 1);
                        """), {"cat_id": cat_id, "name": s_name, "slug": s_slug, "order": s_idx + 1})
                print("[DB MIGRATION] Seeded 5 core portfolio categories and subcategories")
        except Exception as e:
            print(f"[DB MIGRATION NOTE] Seed categories: {e}")

        # 12. Reconcile Existing Projects with Authoritative Portfolio Categories
        try:
            cat_alias_map = {
                "residential": "Residential",
                "residence": "Residential",
                "apartment": "Residential",
                "villa": "Residential",
                "penthouse": "Residential",
                "commercial": "Commercial",
                "hospitality": "Hospitality",
                "restaurant": "Hospitality",
                "cafe": "Hospitality",
                "café": "Hospitality",
                "hotel": "Hospitality",
                "office": "Office",
                "retail": "Retail",
                "showroom": "Retail",
                "boutique": "Retail",
            }

            cats = conn.execute(text("SELECT id, name FROM portfolio_categories;")).fetchall()
            cat_by_name = {c[1].lower(): c[0] for c in cats}
            cat_id_to_name = {c[0]: c[1] for c in cats}

            projects_to_migrate = conn.execute(text("SELECT id, category, project_type, category_id FROM projects;")).fetchall()
            for p_id, p_cat_str, p_type, p_cat_id in projects_to_migrate:
                target_cat_id = p_cat_id
                target_cat_name = None

                if not target_cat_id and p_cat_str:
                    clean_cat = p_cat_str.strip().lower()
                    if clean_cat in cat_by_name:
                        target_cat_id = cat_by_name[clean_cat]
                        target_cat_name = cat_id_to_name[target_cat_id]
                    elif clean_cat in cat_alias_map:
                        canonical = cat_alias_map[clean_cat].lower()
                        if canonical in cat_by_name:
                            target_cat_id = cat_by_name[canonical]
                            target_cat_name = cat_id_to_name[target_cat_id]
                    else:
                        res_id = cat_by_name.get("residential")
                        if res_id:
                            target_cat_id = res_id
                            target_cat_name = "Residential"

                if target_cat_id:
                    canon_name = target_cat_name or cat_id_to_name.get(target_cat_id, "Residential")
                    conn.execute(
                        text("UPDATE projects SET category_id = :cat_id, category = :cat_name WHERE id = :p_id;"),
                        {"cat_id": target_cat_id, "cat_name": canon_name, "p_id": p_id}
                    )
            print("[DB MIGRATION] Reconciled existing projects with authoritative portfolio categories")
        except Exception as e:
            print(f"[DB MIGRATION NOTE] Project category reconciliation: {e}")

        # 13. Reconcile initial representative project for categories if not yet set
        try:
            cats = conn.execute(text("SELECT id, name FROM portfolio_categories;")).fetchall()
            for c_id, c_name in cats:
                current_featured = conn.execute(
                    text("SELECT featured_project_id FROM portfolio_categories WHERE id = :c_id;"),
                    {"c_id": c_id}
                ).fetchone()
                if current_featured and current_featured[0] is None:
                    cand = conn.execute(
                        text("""
                            SELECT id FROM projects 
                            WHERE is_published = 1 AND (category_id = :c_id OR lower(category) = :c_name)
                            ORDER BY featured DESC, id ASC LIMIT 1;
                        """),
                        {"c_id": c_id, "c_name": c_name.lower()}
                    ).fetchone()
                    if cand and cand[0]:
                        conn.execute(
                            text("UPDATE portfolio_categories SET featured_project_id = :p_id WHERE id = :c_id;"),
                            {"p_id": cand[0], "c_id": c_id}
                        )
                        print(f"[DB MIGRATION] Set representative project #{cand[0]} for category '{c_name}'")
        except Exception as e:
            print(f"[DB MIGRATION NOTE] Category representative reconciliation: {e}")

        conn.commit()

