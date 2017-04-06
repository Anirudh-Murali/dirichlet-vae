import numpy as np
import pandas as pd
import random

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

from keras.layers import Input, Dense, Lambda
from keras.models import Model
from keras import backend as K
from keras import metrics


class GaussVae:
    def __init__(self,
                 original_dim,
                 batch_size=32,
                 encoder_widths=50,
                 latent_dim=10,
                 decoder_width=50,
                 logit=False):

        self.batch_size = batch_size
        self.latent_dim = latent_dim
        self.original_dim = original_dim
        self.encoder_widths = encoder_widths
        self.latent_dim = latent_dim
        self.decoder_width = decoder_width
        self.logit = logit

        # Network Specification
        # --------------------
        self.x = Input(batch_shape=(self.batch_size, original_dim))

        # Two-Layer Network learns q(z|x)
        # produces mu(x), log-sigma(x)
        self.q_zx = Dense(self.encoder_widths, activation='relu')
        self.mu = Dense(self.latent_dim)
        self.log_sigma = Dense(self.latent_dim)

        # Reparameterization Trick for Sampling
        def sampling(args):
            z_mean, z_log_var = args
            e = K.random_normal(
                shape=(self.batch_size, self.latent_dim))
            z_star = z_mean + K.exp(z_log_var / 2) * e

            if self.logit:
                return K.softmax(z_star)
            return z_star

        # Two Layer Network learns p(x|z)
        # produces expectation
        self.p_xz = Dense(self.decoder_width, activation='relu')
        self.generator = Dense(self.original_dim, activation='sigmoid')

        # Network Construction
        # -------------------
        z = self.q_zx(self.x)
        z_mu = self.mu(z)
        z_sd = self.log_sigma(z)

        z_star = Lambda(
            sampling,
            output_shape=(self.latent_dim,))([z_mu, z_sd])

        d1 = self.p_xz(z_star)
        x_star = self.generator(d1)

        self.latent_variable = z_mu

        def vae_loss(x, x_star):
            reconstruction_error = (
                self.original_dim * metrics.binary_crossentropy(x, x_star))
            kl = .5 * K.sum(1 + z_sd - K.square(z_mu) - K.exp(z_sd), axis=-1)
            return reconstruction_error - kl

        self.vae = Model(self.x, x_star)
        self.vae.compile(optimizer='adam', loss=vae_loss)

    def _set_encoder(self):
        self.encoder = Model(self.x, self.latent_variable)

    def _set_decoder(self):
        z = Input(shape=(self.latent_dim,))
        d1 = self.p_xz(z)
        x_star = self.generator(d1)
        self.decoder = Model(z, x_star)

    def fit(self, x_train, x_test, **kwargs):
        self.history = (
            self.vae.fit(x=x_train, y=x_train,
                         batch_size=self.batch_size,
                         validation_data=(x_test, x_test),
                         **kwargs))
        self._set_encoder()
        self._set_decoder()

    def encode(self, X):
        z_star = self.encoder.predict(X)
        return z_star

    def decode(self, L):
        reconstruction = self.decoder.predict(L)
        return reconstruction


