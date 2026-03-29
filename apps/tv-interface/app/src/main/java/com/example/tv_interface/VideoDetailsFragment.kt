package com.example.tv_interface

import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.os.Bundle
import android.graphics.drawable.Drawable
import androidx.leanback.app.DetailsSupportFragment
import androidx.leanback.app.DetailsSupportFragmentBackgroundController
import androidx.leanback.widget.Action
import androidx.leanback.widget.ArrayObjectAdapter
import androidx.leanback.widget.ClassPresenterSelector
import androidx.leanback.widget.DetailsOverviewRow
import androidx.leanback.widget.FullWidthDetailsOverviewRowPresenter
import androidx.leanback.widget.FullWidthDetailsOverviewSharedElementHelper
import androidx.leanback.widget.HeaderItem
import androidx.leanback.widget.ImageCardView
import androidx.leanback.widget.ListRow
import androidx.leanback.widget.ListRowPresenter
import androidx.leanback.widget.OnActionClickedListener
import androidx.leanback.widget.OnItemViewClickedListener
import androidx.leanback.widget.Presenter
import androidx.leanback.widget.Row
import androidx.leanback.widget.RowPresenter
import androidx.core.app.ActivityOptionsCompat
import androidx.core.content.ContextCompat
import android.util.Log
import android.widget.Toast

import com.bumptech.glide.Glide
import com.bumptech.glide.request.target.SimpleTarget
import com.bumptech.glide.request.transition.Transition

import java.util.Collections

/**
 * A wrapper fragment for Alice Home OS details screens.
 * It shows a detailed view of an entity and its metadata plus related entities.
 */
class VideoDetailsFragment : DetailsSupportFragment() {

    private var mSelectedEntity: HomeEntity? = null

    private lateinit var mDetailsBackground: DetailsSupportFragmentBackgroundController
    private lateinit var mPresenterSelector: ClassPresenterSelector
    private lateinit var mAdapter: ArrayObjectAdapter

    override fun onCreate(savedInstanceState: Bundle?) {
        Log.d(TAG, "onCreate DetailsFragment")
        super.onCreate(savedInstanceState)

        mDetailsBackground = DetailsSupportFragmentBackgroundController(this)

        mSelectedEntity = activity!!.intent.getSerializableExtra(DetailsActivity.ENTITY) as? HomeEntity
        if (mSelectedEntity != null) {
            mPresenterSelector = ClassPresenterSelector()
            mAdapter = ArrayObjectAdapter(mPresenterSelector)
            setupDetailsOverviewRow()
            setupDetailsOverviewRowPresenter()
            setupRelatedEntityListRow()
            adapter = mAdapter
            initializeBackground(mSelectedEntity)
            onItemViewClickedListener = ItemViewClickedListener()
        } else {
            val intent = Intent(activity!!, MainActivity::class.java)
            startActivity(intent)
        }
    }

    private fun initializeBackground(entity: HomeEntity?) {
        mDetailsBackground.enableParallax()
        Glide.with(activity!!)
            .asBitmap()
            .centerCrop()
            .error(R.drawable.default_background)
            .load(entity?.backgroundUrl)
            .into<SimpleTarget<Bitmap>>(object : SimpleTarget<Bitmap>() {
                override fun onResourceReady(
                    bitmap: Bitmap,
                    transition: Transition<in Bitmap>?
                ) {
                    mDetailsBackground.coverBitmap = bitmap
                    mAdapter.notifyArrayItemRangeChanged(0, mAdapter.size())
                }
            })
    }

    private fun setupDetailsOverviewRow() {
        val selectedEntity = mSelectedEntity ?: return
        Log.d(TAG, "doInBackground: " + selectedEntity.toString())
        val row = DetailsOverviewRow(selectedEntity)
        row.imageDrawable = ContextCompat.getDrawable(activity!!, R.drawable.default_background)
        val width = convertDpToPixel(activity!!, DETAIL_THUMB_WIDTH)
        val height = convertDpToPixel(activity!!, DETAIL_THUMB_HEIGHT)
        Glide.with(activity!!)
            .load(selectedEntity.iconUrl)
            .centerCrop()
            .error(R.drawable.default_background)
            .into<SimpleTarget<Drawable>>(object : SimpleTarget<Drawable>(width, height) {
                override fun onResourceReady(
                    drawable: Drawable,
                    transition: Transition<in Drawable>?
                ) {
                    Log.d(TAG, "details overview card image url ready: " + drawable)
                    row.imageDrawable = drawable
                    mAdapter.notifyArrayItemRangeChanged(0, mAdapter.size())
                }
            })

        val actionAdapter = ArrayObjectAdapter()

        val toggleLabel = if (selectedEntity.state == "ON") "DEACTIVATE" else "ACTIVATE"
        actionAdapter.add(
            Action(
                ACTION_TOGGLE,
                toggleLabel,
                selectedEntity.state
            )
        )
        actionAdapter.add(
            Action(
                ACTION_SCHEDULE,
                "SCHEDULE",
                "Set automation"
            )
        )
        actionAdapter.add(
            Action(
                ACTION_LOGS,
                "VIEW LOGS",
                "Audit history"
            )
        )
        row.actionsAdapter = actionAdapter

        mAdapter.add(row)
    }

    private fun setupDetailsOverviewRowPresenter() {
        // Set detail background.
        val detailsPresenter = FullWidthDetailsOverviewRowPresenter(DetailsDescriptionPresenter())
        detailsPresenter.backgroundColor =
            ContextCompat.getColor(activity!!, R.color.selected_background)

        // Hook up transition element.
        val sharedElementHelper = FullWidthDetailsOverviewSharedElementHelper()
        sharedElementHelper.setSharedElementEnterTransition(
            activity, DetailsActivity.SHARED_ELEMENT_NAME
        )
        detailsPresenter.setListener(sharedElementHelper)
        detailsPresenter.isParticipatingEntranceTransition = true

        detailsPresenter.onActionClickedListener = OnActionClickedListener { action ->
            if (action.id == ACTION_TOGGLE) {
                mSelectedEntity?.let {
                    it.state = if (it.state == "ON") "OFF" else "ON"
                    Toast.makeText(activity!!, "${it.name} is now ${it.state}", Toast.LENGTH_SHORT).show()
                    // Re-setup the row or update it
                    setupDetailsOverviewRow()
                }
            } else {
                Toast.makeText(activity!!, action.toString(), Toast.LENGTH_SHORT).show()
            }
        }
        mPresenterSelector.addClassPresenter(DetailsOverviewRow::class.java, detailsPresenter)
    }

    private fun setupRelatedEntityListRow() {
        val subcategories = arrayOf(getString(R.string.related_movies)) // "Device Controls"
        val list = HomeList.list

        val listRowAdapter = ArrayObjectAdapter(CardPresenter())
        for (j in list.indices) {
            listRowAdapter.add(list[j])
        }

        val header = HeaderItem(0, subcategories[0])
        mAdapter.add(ListRow(header, listRowAdapter))
        mPresenterSelector.addClassPresenter(ListRow::class.java, ListRowPresenter())
    }

    private fun convertDpToPixel(context: Context, dp: Int): Int {
        val density = context.applicationContext.resources.displayMetrics.density
        return Math.round(dp.toFloat() * density)
    }

    private inner class ItemViewClickedListener : OnItemViewClickedListener {
        override fun onItemClicked(
            itemViewHolder: Presenter.ViewHolder?,
            item: Any?,
            rowViewHolder: RowPresenter.ViewHolder,
            row: Row
        ) {
            if (item is HomeEntity) {
                Log.d(TAG, "Item: " + item.toString())
                val intent = Intent(activity!!, DetailsActivity::class.java)
                intent.putExtra(DetailsActivity.ENTITY, item)
                val sharedView = (itemViewHolder?.view as? ImageCardView)?.mainImageView
                    ?: itemViewHolder?.view
                    ?: return

                val bundle =
                    ActivityOptionsCompat.makeSceneTransitionAnimation(
                        activity!!,
                        sharedView,
                        DetailsActivity.SHARED_ELEMENT_NAME
                    )
                        .toBundle()
                startActivity(intent, bundle)
            }
        }
    }

    companion object {
        private val TAG = "VideoDetailsFragment"

        private val ACTION_TOGGLE = 1L
        private val ACTION_SCHEDULE = 2L
        private val ACTION_LOGS = 3L

        private val DETAIL_THUMB_WIDTH = 274
        private val DETAIL_THUMB_HEIGHT = 274
    }
}