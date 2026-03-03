import { STOPWORDS } from "./stopwords.js";

let MODEL = null;

export async function loadModel() {
  if (MODEL) return MODEL;

  // In a Chrome extension, use chrome.runtime.getURL to resolve the JSON path
  const url =
    typeof chrome !== "undefined" && chrome.runtime && chrome.runtime.getURL
      ? chrome.runtime.getURL("model.json")
      : new URL("./model.json", import.meta.url).toString();

  const response = await fetch(url);
  MODEL = await response.json();

  return MODEL;
}

function tokenize(text) {
  return text
    .toLowerCase()
    .replace(/[^\w\s]/g, "")
    .split(/\s+/)
    .filter((word) => word.length > 0 && !STOPWORDS.has(word));
}

function generateNgrams(tokens) {
  const ngrams = [...tokens]; // unigrams

  for (let i = 0; i < tokens.length - 1; i++) {
    ngrams.push(tokens[i] + " " + tokens[i + 1]);
  }

  return ngrams;
}

function computeTF(ngrams, vocabSize) {
  const tf = new Array(vocabSize).fill(0);

  ngrams.forEach((term) => {
    const idx = MODEL.vocab[term];
    if (idx !== undefined) {
      tf[idx] += 1;
    }
  });

  return tf;
}

function applyTFIDF(tf) {
  return tf.map((val, i) => val * MODEL.idf[i]);
}

function normalize(vec) {
  let norm = 0;

  for (let v of vec) norm += v * v;

  norm = Math.sqrt(norm);

  if (norm === 0) return vec;

  return vec.map((v) => v / norm);
}

function sigmoid(z) {
  return 1 / (1 + Math.exp(-z));
}

function predictProbability(features) {
  let score = MODEL.bias;

  for (let i = 0; i < features.length; i++) {
    score += features[i] * MODEL.weights[i];
  }

  return sigmoid(score);
}

export function classify(query) {
  const tokens = tokenize(query);
  const ngrams = generateNgrams(tokens);
  const tf = computeTF(ngrams, MODEL.idf.length);
  let tfidf = applyTFIDF(tf);
  tfidf = normalize(tfidf);
  const probLLM = predictProbability(tfidf);

  return {
    route: probLLM > 0.5 ? "llm" : "search",
    confidence: Math.max(probLLM, 1 - probLLM),
  };
}

