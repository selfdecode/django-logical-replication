CREATE TABLE public.auth_group (
    id integer NOT NULL,
    name character varying(150) NOT NULL
);

CREATE SEQUENCE public.auth_group_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

ALTER SEQUENCE public.auth_group_id_seq OWNED BY public.auth_group.id;

CREATE TABLE public.auth_group_permissions (
    id bigint NOT NULL,
    group_id integer NOT NULL,
    permission_id integer NOT NULL
);

CREATE SEQUENCE public.auth_group_permissions_id_seq START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

ALTER SEQUENCE public.auth_group_permissions_id_seq OWNED BY public.auth_group_permissions.id;

CREATE TABLE public.auth_permission (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    content_type_id integer NOT NULL,
    codename character varying(100) NOT NULL
);

CREATE SEQUENCE public.auth_permission_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

ALTER SEQUENCE public.auth_permission_id_seq OWNED BY public.auth_permission.id;

CREATE TABLE public.auth_user (
    id integer NOT NULL,
    password character varying(128) NOT NULL,
    last_login timestamp with time zone,
    is_superuser boolean NOT NULL,
    username character varying(150) NOT NULL,
    first_name character varying(150) NOT NULL,
    last_name character varying(150) NOT NULL,
    email character varying(254) NOT NULL,
    is_staff boolean NOT NULL,
    is_active boolean NOT NULL,
    date_joined timestamp with time zone NOT NULL
);

CREATE TABLE public.auth_user_groups (
    id bigint NOT NULL,
    user_id integer NOT NULL,
    group_id integer NOT NULL
);

CREATE SEQUENCE public.auth_user_groups_id_seq START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

ALTER SEQUENCE public.auth_user_groups_id_seq OWNED BY public.auth_user_groups.id;

CREATE SEQUENCE public.auth_user_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

ALTER SEQUENCE public.auth_user_id_seq OWNED BY public.auth_user.id;

CREATE TABLE public.auth_user_user_permissions (
    id bigint NOT NULL,
    user_id integer NOT NULL,
    permission_id integer NOT NULL
);

CREATE SEQUENCE public.auth_user_user_permissions_id_seq START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

ALTER SEQUENCE public.auth_user_user_permissions_id_seq OWNED BY public.auth_user_user_permissions.id;

CREATE TABLE public.django_content_type (
    id integer NOT NULL,
    app_label character varying(100) NOT NULL,
    model character varying(100) NOT NULL
);

CREATE SEQUENCE public.django_content_type_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

ALTER SEQUENCE public.django_content_type_id_seq OWNED BY public.django_content_type.id;

ALTER TABLE
    ONLY public.auth_group
ALTER COLUMN
    id
SET
    DEFAULT nextval('public.auth_group_id_seq' :: regclass);

ALTER TABLE
    ONLY public.auth_group_permissions
ALTER COLUMN
    id
SET
    DEFAULT nextval(
        'public.auth_group_permissions_id_seq' :: regclass
    );

ALTER TABLE
    ONLY public.auth_permission
ALTER COLUMN
    id
SET
    DEFAULT nextval('public.auth_permission_id_seq' :: regclass);

ALTER TABLE
    ONLY public.auth_user
ALTER COLUMN
    id
SET
    DEFAULT nextval('public.auth_user_id_seq' :: regclass);

ALTER TABLE
    ONLY public.auth_user_groups
ALTER COLUMN
    id
SET
    DEFAULT nextval('public.auth_user_groups_id_seq' :: regclass);

ALTER TABLE
    ONLY public.auth_user_user_permissions
ALTER COLUMN
    id
SET
    DEFAULT nextval(
        'public.auth_user_user_permissions_id_seq' :: regclass
    );

ALTER TABLE
    ONLY public.django_content_type
ALTER COLUMN
    id
SET
    DEFAULT nextval('public.django_content_type_id_seq' :: regclass);

ALTER TABLE
    ONLY public.auth_group
ADD
    CONSTRAINT auth_group_name_key UNIQUE (name);

ALTER TABLE
    ONLY public.auth_group_permissions
ADD
    CONSTRAINT auth_group_permissions_group_id_permission_id_0cd325b0_uniq UNIQUE (group_id, permission_id);

ALTER TABLE
    ONLY public.auth_group_permissions
ADD
    CONSTRAINT auth_group_permissions_pkey PRIMARY KEY (id);

ALTER TABLE
    ONLY public.auth_group
ADD
    CONSTRAINT auth_group_pkey PRIMARY KEY (id);

ALTER TABLE
    ONLY public.auth_permission
ADD
    CONSTRAINT auth_permission_content_type_id_codename_01ab375a_uniq UNIQUE (content_type_id, codename);

ALTER TABLE
    ONLY public.auth_permission
ADD
    CONSTRAINT auth_permission_pkey PRIMARY KEY (id);

ALTER TABLE
    ONLY public.auth_user_groups
ADD
    CONSTRAINT auth_user_groups_pkey PRIMARY KEY (id);

ALTER TABLE
    ONLY public.auth_user_groups
ADD
    CONSTRAINT auth_user_groups_user_id_group_id_94350c0c_uniq UNIQUE (user_id, group_id);

ALTER TABLE
    ONLY public.auth_user
ADD
    CONSTRAINT auth_user_pkey PRIMARY KEY (id);

ALTER TABLE
    ONLY public.auth_user_user_permissions
ADD
    CONSTRAINT auth_user_user_permissions_pkey PRIMARY KEY (id);

ALTER TABLE
    ONLY public.auth_user_user_permissions
ADD
    CONSTRAINT auth_user_user_permissions_user_id_permission_id_14a6b632_uniq UNIQUE (user_id, permission_id);

ALTER TABLE
    ONLY public.auth_user
ADD
    CONSTRAINT auth_user_username_key UNIQUE (username);

ALTER TABLE
    ONLY public.django_content_type
ADD
    CONSTRAINT django_content_type_app_label_model_76bd3d3b_uniq UNIQUE (app_label, model);

ALTER TABLE
    ONLY public.django_content_type
ADD
    CONSTRAINT django_content_type_pkey PRIMARY KEY (id);

CREATE INDEX auth_group_name_a6ea08ec_like ON public.auth_group USING btree (name varchar_pattern_ops);

CREATE INDEX auth_group_permissions_group_id_b120cbf9 ON public.auth_group_permissions USING btree (group_id);

CREATE INDEX auth_group_permissions_permission_id_84c5c92e ON public.auth_group_permissions USING btree (permission_id);

CREATE INDEX auth_permission_content_type_id_2f476e4b ON public.auth_permission USING btree (content_type_id);

CREATE INDEX auth_user_groups_group_id_97559544 ON public.auth_user_groups USING btree (group_id);

CREATE INDEX auth_user_groups_user_id_6a12ed8b ON public.auth_user_groups USING btree (user_id);

CREATE INDEX auth_user_user_permissions_permission_id_1fbb5f2c ON public.auth_user_user_permissions USING btree (permission_id);

CREATE INDEX auth_user_user_permissions_user_id_a95ead1b ON public.auth_user_user_permissions USING btree (user_id);

CREATE INDEX auth_user_username_6821ab7c_like ON public.auth_user USING btree (username varchar_pattern_ops);

ALTER TABLE
    ONLY public.auth_group_permissions
ADD
    CONSTRAINT auth_group_permissio_permission_id_84c5c92e_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE
    ONLY public.auth_group_permissions
ADD
    CONSTRAINT auth_group_permissions_group_id_b120cbf9_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE
    ONLY public.auth_permission
ADD
    CONSTRAINT auth_permission_content_type_id_2f476e4b_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE
    ONLY public.auth_user_groups
ADD
    CONSTRAINT auth_user_groups_group_id_97559544_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE
    ONLY public.auth_user_groups
ADD
    CONSTRAINT auth_user_groups_user_id_6a12ed8b_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE
    ONLY public.auth_user_user_permissions
ADD
    CONSTRAINT auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE
    ONLY public.auth_user_user_permissions
ADD
    CONSTRAINT auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;
