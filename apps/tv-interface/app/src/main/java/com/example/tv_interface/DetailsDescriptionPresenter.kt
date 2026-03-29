package com.example.tv_interface

import androidx.leanback.widget.AbstractDetailsDescriptionPresenter

class DetailsDescriptionPresenter : AbstractDetailsDescriptionPresenter() {

    override fun onBindDescription(
        viewHolder: AbstractDetailsDescriptionPresenter.ViewHolder,
        item: Any
    ) {
        val entity = item as HomeEntity

        viewHolder.title.text = entity.name
        viewHolder.subtitle.text = "${entity.room} • ${entity.status}"
        viewHolder.body.text = "Device Type: ${entity.type}\nCurrent State: ${entity.state}\n\nThis device is managed by Alice Home OS. It is a local-first, private entity providing secure interaction within your home network."
    }
}