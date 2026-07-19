<template>
  <KinematicsWorkflowPage :session-id="sessionId" />
</template>

<script setup lang="ts">
import KinematicsWorkflowPage from '../components/kinematics-workflow/KinematicsWorkflowPage.vue'

const props = defineProps<{ sessionId: string }>()
const sessionId = props.sessionId
</script>
