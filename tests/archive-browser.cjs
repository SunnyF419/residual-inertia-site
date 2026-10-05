'use strict';
const assert = require('node:assert/strict');
const {filterRecords, pageRecords, rankRecords} = require('../assets/archive-browser.js');

const records = [
  {text: 'Winners Glide, Losers Stumble Taiyang Feng Momentum 2026-07-10'},
  {text: '市场进入防御，AI 硬件保持强势 2026-10-03 Taiyang Feng'},
  {text: '2026-09-01 Defensive 66.8'},
  {text: '2026-09-02 Caution 64.6'},
];
assert.deepEqual(filterRecords(records, 'TAIYANG momentum'), [records[0]]);
assert.deepEqual(filterRecords(records, 'ＡＩ 防御'), [records[1]]);
assert.deepEqual(filterRecords(records, '2026.09 Defensive'), [records[2]]);
assert.deepEqual(filterRecords(records, '2026/09/02'), [records[3]]);
assert.deepEqual(filterRecords(records, '  \n '), records);
assert.deepEqual(filterRecords(records, '<img src=x onerror=alert(1)>'), []);
assert.deepEqual(filterRecords(records, 'nonexistent'), []);
// Search must reach a match beyond the original first six archive entries.
const collection = Array.from({length: 13}, (_, i) => ({text: `Research ${i}`, id: i}));
assert.equal(filterRecords(collection, 'Research 12')[0].id, 12);
assert.deepEqual([1, 2, 3].flatMap(page => pageRecords(collection, page).items), collection);
assert.equal(pageRecords(collection, 1).items.length, 6);
assert.equal(pageRecords(collection, 2).items.length, 6);
assert.equal(pageRecords(collection, 3).items.length, 1);
assert.equal(pageRecords(collection, 99).page, 3);
assert.equal(pageRecords([], 2).page, 1);
assert.deepEqual(pageRecords([], 1).items, []);
const ranked = [{title:'About', text:'About Winners Glide'}, {title:'Winners Glide', text:'Winners Glide'}, {title:'Research', text:'Research Winners Glide'}];
assert.equal(rankRecords(filterRecords(ranked, 'Winners Glide'), 'Winners Glide')[0].title, 'Winners Glide');
assert.equal(ranked[0].title, 'About');
console.log('PASS: multilingual search, date formats, literal hostile input, complete collection search and six-result pagination.');
