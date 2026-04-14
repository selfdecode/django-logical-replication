CREATE PUBLICATION django_logical_replication_pub;

CREATE PUBLICATION django_logical_replication_upsert_pub WITH (publish = 'insert, update');
