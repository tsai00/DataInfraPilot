CREATE TABLE public.scraper_run_metadata (
	id BIGSERIAL PRIMARY key,
    run_id UUID NOT NULL,
    project VARCHAR(255) NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    pages_total INTEGER,
    items_total INTEGER,
    items_scraped INTEGER,
    is_successful BOOLEAN NOT NULL,
    get_requests_sent INTEGER,
    post_requests_sent INTEGER
);