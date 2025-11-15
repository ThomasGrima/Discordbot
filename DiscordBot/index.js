import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import dotenv from "dotenv";
import OpenAI from "openai";
import { Client, GatewayIntentBits, REST, Routes, SlashCommandBuilder } from "discord.js";

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);


const CHAT_MODEL = "gpt-4o-mini";
const EMBEDDING_MODEL = "text-embedding-3-small";
const MAX_ANSWER_TOKENS = 300;
const MAX_REPLY_CHARS = 900; 
const TOP_K = 4; 


const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
const client = new Client({ intents: [GatewayIntentBits.Guilds] });

const RULES_PATH = path.join(__dirname, "rules.txt");
let CHUNKS = []; 

function simpleChunk(text) {
  
  const parts = text
    .split(/\n\s*\n/g)
    .map(s => s.trim())
    .filter(Boolean);

  return parts.map((p, i) => {
    
    const m = p.match(/^\[(.+?)\]\s*\n?/);
    const section = m ? m[1].trim() : `Section ${i + 1}`;
    const body = m ? p.replace(m[0], "").trim() : p;
    return { id: String(i + 1), section, text: body };
  });
}

function cosine(a, b) {
  let dot = 0, na = 0, nb = 0;
  for (let i = 0; i < a.length; i++) {
    dot += a[i] * b[i];
    na += a[i] * a[i];
    nb += b[i] * b[i];
  }
  return dot / (Math.sqrt(na) * Math.sqrt(nb));
}

async function embedOne(input) {
  const res = await openai.embeddings.create({
    model: EMBEDDING_MODEL,
    input
  });
  return res.data[0].embedding;
}

async function loadAndEmbedRules() {
  const raw = fs.readFileSync(RULES_PATH, "utf8");
  const rawChunks = simpleChunk(raw);

  
  const out = [];
  for (const rc of rawChunks) {
    const emb = await embedOne(rc.text);
    out.push({ ...rc, embedding: emb });
  }
  CHUNKS = out;
  console.log(`Loaded ${CHUNKS.length} rule chunks.`);
}

async function retrieveRelevant(query, k = TOP_K) {
  const qEmb = await embedOne(query);
  return CHUNKS
    .map(c => ({ c, score: cosine(qEmb, c.embedding) }))
    .sort((a, b) => b.score - a.score)
    .slice(0, k)
    .map(s => s.c);
}

const systemPrompt = `
You are a Discord rules assistant. Answer ONLY using the provided RULE EXCERPTS.
If the rules do not specify, reply "Not specified. Please ask a moderator."
Be brief, friendly, and cite sections like [1. Advertising].
Keep the answer under 120 words.
`;

async function answerQuestion(query) {
  const ctx = await retrieveRelevant(query, TOP_K);
  const contextBlock = ctx.map(c => `[${c.section}]\n${c.text}`).join("\n\n");

  const messages = [
    { role: "system", content: systemPrompt },
    { role: "user", content: `RULE EXCERPTS:\n${contextBlock}\n\nQUESTION: ${query}` }
  ];

  const resp = await openai.chat.completions.create({
    model: CHAT_MODEL,
    messages,
    temperature: 0.2,
    max_tokens: MAX_ANSWER_TOKENS
  });

  let text = resp.choices?.[0]?.message?.content?.trim() || "Sorry, I could not generate a reply.";
  
  if (text.length > MAX_REPLY_CHARS) text = text.slice(0, MAX_REPLY_CHARS - 3) + "...";

  const cites = ctx.map(c => `[${c.section}]`).join(" ");
  return `${text}\n${cites}`;
}


const commands = [
  new SlashCommandBuilder()
    .setName("rules")
    .setDescription("Ask a question about the server rules")
    .addStringOption(o => o
      .setName("question")
      .setDescription("Your question")
      .setRequired(true)
    )
].map(c => c.toJSON());

async function registerCommands() {
  const rest = new REST({ version: "10" }).setToken(process.env.DISCORD_BOT_TOKEN);
  await rest.put(
    Routes.applicationCommands(process.env.DISCORD_CLIENT_ID),
    { body: commands }
  );
  console.log("Slash command /rules registered.");
}

client.on("ready", () => {
  console.log(`Logged in as ${client.user.tag}`);
});

client.on("interactionCreate", async (interaction) => {
  try {
    if (!interaction.isChatInputCommand()) return;
    if (interaction.commandName !== "rules") return;

    const q = interaction.options.getString("question", true);

    
    await interaction.deferReply({ ephemeral: true });


    const reply = await answerQuestion(q);
    await interaction.editReply(reply);
  } catch (err) {
    console.error(err);
    if (interaction.isRepliable()) {
      await interaction.reply({ content: "Something went wrong. Please try again.", ephemeral: true }).catch(() => {});
    }
  }
});

(async () => {
  
  if (!process.env.DISCORD_BOT_TOKEN || !process.env.DISCORD_CLIENT_ID || !process.env.OPENAI_API_KEY) {
    console.error("Missing keys. Check your .env file.");
    process.exit(1);
  }
  await loadAndEmbedRules();
  await registerCommands();
  await client.login(process.env.DISCORD_BOT_TOKEN);
})();
