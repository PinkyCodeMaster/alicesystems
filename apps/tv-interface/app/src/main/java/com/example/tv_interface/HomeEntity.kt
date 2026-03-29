package com.example.tv_interface

import java.io.Serializable

/**
 * HomeEntity represents a smart home device or service (light, camera, thermostat).
 */
data class HomeEntity(
    var id: Long = 0,
    var name: String? = null,
    var status: String? = null,
    var room: String? = null,
    var iconUrl: String? = null,
    var backgroundUrl: String? = null,
    var type: EntityType = EntityType.UNKNOWN,
    var state: String? = "OFF"
) : Serializable {

    enum class EntityType {
        LIGHT, CAMERA, THERMOSTAT, SENSOR, ACTUATOR, UNKNOWN
    }

    override fun toString(): String {
        return "HomeEntity{" +
                "id=" + id +
                ", name='" + name + '\'' +
                ", status='" + status + '\'' +
                ", room='" + room + '\'' +
                ", state='" + state + '\'' +
                '}'
    }

    companion object {
        internal const val serialVersionUID = 727566175075960653L
    }
}