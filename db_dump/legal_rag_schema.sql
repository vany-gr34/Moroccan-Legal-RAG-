--
-- PostgreSQL database dump
--

\restrict 0OdBgDbUoM6Owie4kqMRdBDEaPA8JtdS0MbM0HzkX3RII1vycKiltonh5xaR0vi

-- Dumped from database version 16.14 (Debian 16.14-1.pgdg13+1)
-- Dumped by pg_dump version 16.14 (Debian 16.14-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pg_trgm; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;


--
-- Name: EXTENSION pg_trgm; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pg_trgm IS 'text similarity measurement and index searching based on trigrams';


--
-- Name: unaccent; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS unaccent WITH SCHEMA public;


--
-- Name: EXTENSION unaccent; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION unaccent IS 'text search dictionary that removes accents';


--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: app_config; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.app_config (
    id integer NOT NULL,
    config_key character varying(255) NOT NULL,
    config_value text DEFAULT ''::text NOT NULL,
    description text DEFAULT ''::text,
    category character varying(100) DEFAULT 'general'::character varying,
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


--
-- Name: app_config_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.app_config_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: app_config_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.app_config_id_seq OWNED BY public.app_config.id;


--
-- Name: conversations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.conversations (
    id integer NOT NULL,
    session_id character varying(64) NOT NULL,
    role character varying(16) NOT NULL,
    content text NOT NULL,
    sources jsonb,
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamp without time zone DEFAULT now(),
    CONSTRAINT conversations_role_check CHECK (((role)::text = ANY ((ARRAY['user'::character varying, 'assistant'::character varying, 'system'::character varying])::text[])))
);


--
-- Name: conversations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.conversations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: conversations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.conversations_id_seq OWNED BY public.conversations.id;


--
-- Name: legal_chunks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.legal_chunks (
    id integer NOT NULL,
    chunk_text text NOT NULL,
    chunk_text_normalized text NOT NULL,
    embedding public.vector(1024),
    domain character varying(50) NOT NULL,
    law_name character varying(255),
    law_number character varying(50),
    article_number character varying(20),
    source_file character varying(500) NOT NULL,
    source_page integer,
    extraction_method character varying(50),
    ocr_confidence double precision,
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    is_active boolean DEFAULT true,
    chapter_title text,
    section_title text,
    search_vector tsvector,
    CONSTRAINT legal_chunks_domain_check CHECK (((domain)::text = ANY ((ARRAY['traffic'::character varying, 'criminal'::character varying, 'family'::character varying, 'civil'::character varying, 'commercial'::character varying, 'judicial'::character varying, 'violations'::character varying, 'companies'::character varying])::text[]))),
    CONSTRAINT legal_chunks_extraction_method_check CHECK (((extraction_method)::text = ANY ((ARRAY['digital'::character varying, 'ocr'::character varying, 'manual'::character varying, 'pymupdf'::character varying, 'pdfplumber'::character varying, 'pipeline'::character varying])::text[])))
);


--
-- Name: legal_chunks_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.legal_chunks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: legal_chunks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.legal_chunks_id_seq OWNED BY public.legal_chunks.id;


--
-- Name: app_config id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.app_config ALTER COLUMN id SET DEFAULT nextval('public.app_config_id_seq'::regclass);


--
-- Name: conversations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversations ALTER COLUMN id SET DEFAULT nextval('public.conversations_id_seq'::regclass);


--
-- Name: legal_chunks id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.legal_chunks ALTER COLUMN id SET DEFAULT nextval('public.legal_chunks_id_seq'::regclass);


--
-- Name: app_config app_config_config_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.app_config
    ADD CONSTRAINT app_config_config_key_key UNIQUE (config_key);


--
-- Name: app_config app_config_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.app_config
    ADD CONSTRAINT app_config_pkey PRIMARY KEY (id);


--
-- Name: conversations conversations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT conversations_pkey PRIMARY KEY (id);


--
-- Name: legal_chunks legal_chunks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.legal_chunks
    ADD CONSTRAINT legal_chunks_pkey PRIMARY KEY (id);


--
-- Name: idx_app_config_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_app_config_category ON public.app_config USING btree (category);


--
-- Name: idx_app_config_key; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_app_config_key ON public.app_config USING btree (config_key);


--
-- Name: idx_conversations_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_conversations_created ON public.conversations USING btree (created_at);


--
-- Name: idx_conversations_session; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_conversations_session ON public.conversations USING btree (session_id);


--
-- Name: idx_legal_chunks_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_legal_chunks_active ON public.legal_chunks USING btree (is_active);


--
-- Name: idx_legal_chunks_article; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_legal_chunks_article ON public.legal_chunks USING btree (article_number);


--
-- Name: idx_legal_chunks_domain; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_legal_chunks_domain ON public.legal_chunks USING btree (domain);


--
-- Name: idx_legal_chunks_embedding; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_legal_chunks_embedding ON public.legal_chunks USING hnsw (embedding public.vector_cosine_ops) WITH (m='16', ef_construction='200');


--
-- Name: idx_legal_chunks_search; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_legal_chunks_search ON public.legal_chunks USING gin (search_vector);


--
-- Name: idx_legal_chunks_source; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_legal_chunks_source ON public.legal_chunks USING btree (source_file);


--
-- PostgreSQL database dump complete
--

\unrestrict 0OdBgDbUoM6Owie4kqMRdBDEaPA8JtdS0MbM0HzkX3RII1vycKiltonh5xaR0vi

