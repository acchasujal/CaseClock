const express = require("express");
const cors = require("cors");

const app = express();

app.use(cors());

app.use(express.json());

app.get("/health", (req, res) => {
    res.json({
        status: "ok",
        service: "CaseClock AppSail Spike"
    });
});

app.get("/hello", (req, res) => {
    res.json({
        message: "Hello Catalyst"
    });
});

app.post("/echo", (req, res) => {
    res.json(req.body);
});

const PORT = process.env.X_ZOHO_CATALYST_LISTEN_PORT || 9000;

app.listen(PORT, () => {
    console.log(`Listening on ${PORT}`);
});