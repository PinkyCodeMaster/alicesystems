package expo.modules.alicewifiprovisioning

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import android.net.wifi.WifiNetworkSpecifier
import android.os.Build
import android.os.Handler
import android.os.Looper
import expo.modules.kotlin.Promise
import expo.modules.kotlin.exception.CodedException
import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition

private const val DEFAULT_TIMEOUT_MS = 30000L

class AliceWifiProvisioningModule : Module() {
  private val mainHandler = Handler(Looper.getMainLooper())
  private var activeNetworkCallback: ConnectivityManager.NetworkCallback? = null
  private var activeNetwork: Network? = null
  private var pendingTimeout: Runnable? = null

  private val connectivityManager: ConnectivityManager
    get() {
      val reactContext = appContext.reactContext ?: throw WifiProvisioningException(
        "React context is unavailable."
      )
      return reactContext.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager
        ?: throw WifiProvisioningException("Connectivity manager is unavailable.")
    }

  override fun definition() = ModuleDefinition {
    Name("AliceWifiProvisioning")

    AsyncFunction("isAvailableAsync") {
      Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q
    }

    AsyncFunction("connectToSetupApAsync") {
        ssid: String,
        passphrase: String?,
        timeoutMs: Int?,
        promise: Promise ->
      connectToSetupAp(ssid, passphrase, timeoutMs?.toLong() ?: DEFAULT_TIMEOUT_MS, promise)
    }

    AsyncFunction("releaseWifiBindingAsync") {
      releaseBinding()
      true
    }

    AsyncFunction("getCurrentLinkStateAsync") {
      mapOf(
        "bound" to (activeNetwork != null),
        "hasRequestedNetwork" to (activeNetworkCallback != null)
      )
    }

    OnDestroy {
      releaseBinding()
    }
  }

  @Suppress("MissingPermission")
  private fun connectToSetupAp(
    ssid: String,
    passphrase: String?,
    timeoutMs: Long,
    promise: Promise
  ) {
    if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) {
      promise.reject(
        WifiProvisioningException("Android 10 or newer is required for setup Wi-Fi handoff.")
      )
      return
    }

    val targetSsid = ssid.trim()
    if (targetSsid.isEmpty()) {
      promise.reject(WifiProvisioningException("A device setup Wi-Fi name is required."))
      return
    }

    releaseBinding()

    val networkSpecifierBuilder = WifiNetworkSpecifier.Builder()
      .setSsid(targetSsid)

    val trimmedPassphrase = passphrase?.trim().orEmpty()
    if (trimmedPassphrase.isNotEmpty()) {
      networkSpecifierBuilder.setWpa2Passphrase(trimmedPassphrase)
    }

    val request = NetworkRequest.Builder()
      .addTransportType(NetworkCapabilities.TRANSPORT_WIFI)
      .setNetworkSpecifier(networkSpecifierBuilder.build())
      .build()

    var completed = false

    val callback = object : ConnectivityManager.NetworkCallback() {
      override fun onAvailable(network: Network) {
        if (completed) {
          return
        }
        completed = true
        clearPendingTimeout()
        activeNetwork = network
        activeNetworkCallback = this
        connectivityManager.bindProcessToNetwork(network)
        promise.resolve(
          mapOf(
            "ssid" to targetSsid,
            "bound" to true
          )
        )
      }

      override fun onUnavailable() {
        if (completed) {
          return
        }
        completed = true
        clearPendingTimeout()
        unregisterCallback(this)
        promise.reject(WifiProvisioningException("Unable to join $targetSsid."))
      }

      override fun onLost(network: Network) {
        if (activeNetwork == network) {
          connectivityManager.bindProcessToNetwork(null)
          activeNetwork = null
        }
      }
    }

    activeNetworkCallback = callback
    connectivityManager.requestNetwork(request, callback)

    val timeoutRunnable = Runnable {
      if (completed) {
        return@Runnable
      }
      completed = true
      unregisterCallback(callback)
      promise.reject(WifiProvisioningException("Timed out joining $targetSsid."))
    }
    pendingTimeout = timeoutRunnable
    mainHandler.postDelayed(timeoutRunnable, timeoutMs.coerceAtLeast(5000L))
  }

  private fun releaseBinding() {
    clearPendingTimeout()
    connectivityManager.bindProcessToNetwork(null)
    activeNetwork = null
    activeNetworkCallback?.let { unregisterCallback(it) }
    activeNetworkCallback = null
  }

  private fun clearPendingTimeout() {
    pendingTimeout?.let { mainHandler.removeCallbacks(it) }
    pendingTimeout = null
  }

  private fun unregisterCallback(callback: ConnectivityManager.NetworkCallback) {
    try {
      connectivityManager.unregisterNetworkCallback(callback)
    } catch (_: Exception) {
    }
    if (activeNetworkCallback == callback) {
      activeNetworkCallback = null
    }
  }
}

private class WifiProvisioningException(message: String) : CodedException(message)
