package com.example.tv_interface

object HomeList {
    val CATEGORIES = arrayOf(
        "LIVING ROOM",
        "KITCHEN",
        "BEDROOM",
        "SECURITY",
        "SYSTEM"
    )

    val list: List<HomeEntity> by lazy {
        setupEntities()
    }
    private var count: Long = 0

    private fun setupEntities(): List<HomeEntity> {
        val names = arrayOf(
            "Main Light",
            "Front Door Camera",
            "Smart Thermostat",
            "Kitchen Light",
            "Motion Sensor"
        )

        val rooms = arrayOf(
            "Living Room",
            "Exterior",
            "Hallway",
            "Kitchen",
            "Living Room"
        )

        val types = arrayOf(
            HomeEntity.EntityType.LIGHT,
            HomeEntity.EntityType.CAMERA,
            HomeEntity.EntityType.THERMOSTAT,
            HomeEntity.EntityType.LIGHT,
            HomeEntity.EntityType.SENSOR
        )

        // Using placeholder images for now
        val iconUrl = "https://images.unsplash.com/photo-1558002038-1055907df827?q=80&w=200&auto=format&fit=crop"
        val bgUrl = "https://images.unsplash.com/photo-1558002038-1055907df827?q=80&w=1920&auto=format&fit=crop"

        return names.indices.map {
            val entity = HomeEntity()
            entity.id = count++
            entity.name = names[it]
            entity.room = rooms[it]
            entity.type = types[it]
            entity.status = "Connected"
            entity.state = if (it % 2 == 0) "ON" else "OFF"
            entity.iconUrl = iconUrl
            entity.backgroundUrl = bgUrl
            entity
        }
    }
}