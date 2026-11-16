import "dotenv/config";
import pg from "pg";

const { Pool } = pg;

// Only say whether config is present. Host, user and database names stay out of the logs.
if (process.env.NODE_ENV !== "production") {
  console.log(
    "Database config loaded:",
    Boolean(process.env.DATABASE_URL || process.env.DB_HOST)
  );
}

const pool = new Pool(
  process.env.DATABASE_URL
    ? {
        connectionString: process.env.DATABASE_URL,
        connectionTimeoutMillis: 1500,
      }
    : {
        host: process.env.DB_HOST,
        port: Number(process.env.DB_PORT),
        database: process.env.DB_NAME,
        user: process.env.DB_USER,
        password: process.env.DB_PASSWORD,
        connectionTimeoutMillis: 1500,
      }
);

pool.on("error", (err) => {
  console.error("[db] PostgreSQL pool error:", err.code || "", err.message);
});

export default pool;
