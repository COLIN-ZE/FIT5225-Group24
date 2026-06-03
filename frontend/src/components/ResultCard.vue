<template>
  <article class="result-card" :class="{ selected }">
    <label class="select-box" :title="selected ? 'Selected' : 'Select file'">
      <input
        type="checkbox"
        :checked="selected"
        @change="$emit('toggle-select', record.fileId)"
      />
    </label>

    <button class="thumb-button" type="button" @click="$emit('preview', record)">
      <img v-if="record.thumbnailUrl" :src="record.thumbnailUrl" alt="" />
      <span v-else class="thumb-placeholder">No preview</span>
    </button>

    <div class="result-main">
      <div class="title-row">
        <div>
          <h3>{{ record.fileName }}</h3>
          <p>{{ record.fileKey }}</p>
        </div>
        <span class="count-pill">{{ record.count }} detected</span>
      </div>

      <div class="species-row">
        <span class="species">{{ record.species }}</span>
        <span v-if="record.commonName" class="common-name">{{ record.commonName }}</span>
        <span class="confidence">{{ confidenceLabel }}</span>
      </div>

      <div class="tag-row">
        <span v-for="tag in record.tags" :key="tag" class="tag">{{ tag }}</span>
        <span v-if="!record.tags.length" class="empty-tags">No tags</span>
      </div>

      <div class="action-row">
        <input
          v-model="tagText"
          type="text"
          placeholder="Add tags, comma separated"
          @keydown.enter.prevent="submitTags"
        />
        <button type="button" class="btn-secondary" @click="submitTags">Add Tags</button>
        <button type="button" class="btn-danger" @click="$emit('delete', record)">Delete</button>
      </div>
    </div>
  </article>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  record: {
    type: Object,
    required: true,
  },
  selected: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['toggle-select', 'preview', 'add-tags', 'delete'])
const tagText = ref('')

const confidenceLabel = computed(() => `${(props.record.confidence * 100).toFixed(1)}%`)

function submitTags() {
  const tags = tagText.value.split(',').map(tag => tag.trim()).filter(Boolean)
  if (!tags.length) return
  emit('add-tags', props.record, tags)
  tagText.value = ''
}
</script>

<style scoped>
.result-card {
  display: grid;
  grid-template-columns: 24px 112px 1fr;
  gap: 16px;
  align-items: start;
  padding: 16px;
  background: white;
  border: 1px solid #e4e9f0;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(20, 32, 48, 0.06);
}

.result-card.selected {
  border-color: #4a90e2;
  box-shadow: 0 0 0 2px rgba(74, 144, 226, 0.14);
}

.select-box {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 90px;
}

.select-box input {
  width: 16px;
  height: 16px;
}

.thumb-button {
  width: 112px;
  height: 90px;
  padding: 0;
  overflow: hidden;
  border: 1px solid #d9e2ec;
  border-radius: 6px;
  background: #f7fafc;
  cursor: pointer;
}

.thumb-button img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.thumb-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #8795a1;
  font-size: 12px;
}

.result-main {
  min-width: 0;
}

.title-row {
  display: flex;
  gap: 12px;
  justify-content: space-between;
  align-items: flex-start;
}

h3 {
  margin: 0;
  color: #172033;
  font-size: 15px;
  line-height: 1.3;
  word-break: break-word;
}

p {
  margin: 4px 0 0;
  color: #6b7785;
  font-size: 12px;
  word-break: break-word;
}

.count-pill {
  flex-shrink: 0;
  padding: 3px 8px;
  border-radius: 999px;
  background: #eaf4ec;
  color: #2f7d46;
  font-size: 12px;
  font-weight: 700;
}

.species-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 12px;
}

.species {
  color: #172033;
  font-style: italic;
  font-weight: 700;
}

.common-name {
  color: #6b7785;
  font-size: 13px;
}

.confidence {
  margin-left: auto;
  color: #4a90e2;
  font-size: 13px;
  font-weight: 700;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 12px;
}

.tag {
  padding: 3px 8px;
  border-radius: 4px;
  background: #eef2f6;
  color: #435466;
  font-size: 12px;
}

.empty-tags {
  color: #8795a1;
  font-size: 12px;
}

.action-row {
  display: grid;
  grid-template-columns: minmax(150px, 1fr) auto auto;
  gap: 8px;
  margin-top: 14px;
}

.action-row input {
  min-width: 0;
  padding: 8px 10px;
  border: 1px solid #d9e2ec;
  border-radius: 6px;
  font-size: 13px;
}

button {
  font: inherit;
}

.btn-secondary,
.btn-danger {
  border: none;
  border-radius: 6px;
  padding: 8px 10px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
}

.btn-secondary {
  background: #e8f2ff;
  color: #2f6fb3;
}

.btn-danger {
  background: #fdebea;
  color: #c0392b;
}

@media (max-width: 680px) {
  .result-card {
    grid-template-columns: 24px 86px 1fr;
    gap: 12px;
    padding: 12px;
  }

  .thumb-button {
    width: 86px;
    height: 72px;
  }

  .title-row,
  .species-row {
    align-items: flex-start;
  }

  .confidence {
    margin-left: 0;
  }

  .action-row {
    grid-template-columns: 1fr;
  }
}
</style>
