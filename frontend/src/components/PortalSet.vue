<template>
  <div class="ui styled accordion">
    <div class="title"><i class="dropdown icon"></i>Portal List</div>
    <div class="content">
      <div class="accordion">
        <!-- 这里循环标签 -->
        <div class="title"><i class="dropdown icon"></i> 城市 </div>
        <div class="content">
          <div class="accordion">
          <!-- 这里插入pos -->
            <div class="title"><i class="dropdown icon"></i> po名 </div>
            <div class="content">

            </div>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script>
  export default {
    name: 'PortalSet',
    data () {
      return {

      }
    },
    mounted: function () {
      const self = this
      this.axios.get('/api/portals')
    }
  }
</script>
